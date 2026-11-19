"""Un adaptador por modelo fundacional: cargar(modelo, H) -> predecir(contextos [B, C]) -> (punto, q10, q90), [B, H].

El punto es la mediana (se evalúa con MAE). Cada adaptador procesa en lotes internos para la GPU.
"""

import numpy as np
import torch

DISPOSITIVO = "cuda" if torch.cuda.is_available() else "cpu"


def _por_lotes(funcion, contextos, lote):
    """Aplica la función por lotes; si la GPU se queda sin memoria, reduce el lote a la mitad y sigue."""
    partes, i = [], 0
    while i < len(contextos):
        try:
            partes.append(funcion(contextos[i:i + lote]))
            i += lote
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
            if lote == 1:
                raise
            lote = max(1, lote // 2)
            print("sin memoria: lote", lote, flush=True)
    return tuple(np.concatenate([p[k] for p in partes]).astype(np.float32) for k in range(3))


def _np(t):
    return t.detach().float().cpu().numpy() if torch.is_tensor(t) else np.asarray(t, dtype=np.float32)


def chronos2(H, lote=512):
    from chronos import Chronos2Pipeline

    pipe = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map=DISPOSITIVO)

    def f(ctx):
        q, _ = pipe.predict_quantiles(ctx[:, None, :], prediction_length=H, quantile_levels=[0.1, 0.5, 0.9],
                                      batch_size=lote, context_length=ctx.shape[1])
        q = np.stack([_np(x)[0] for x in q])  # [B, H, 3]
        return q[:, :, 1], q[:, :, 0], q[:, :, 2]

    return lambda c: _por_lotes(f, c, lote)


def timesfm25(H, lote=256):
    import timesfm

    m = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
    estado = {}

    def f(ctx):
        if estado.get("c") != ctx.shape[1]:
            m.compile(timesfm.ForecastConfig(max_context=ctx.shape[1], max_horizon=64, normalize_inputs=True,
                                             use_continuous_quantile_head=True, force_flip_invariance=True,
                                             infer_is_positive=True, fix_quantile_crossing=True,
                                             per_core_batch_size=lote))
            estado["c"] = ctx.shape[1]
        _, q = m.forecast(horizon=H, inputs=list(ctx))  # q: [B, H, 10] = media, q10..q90
        q = _np(q)
        return q[:, :, 5], q[:, :, 1], q[:, :, 9]

    return lambda c: _por_lotes(f, c, 2048)


def timesfm3(H, lote=128):
    from timesfm3 import TimesFM3Forecaster

    fc = TimesFM3Forecaster.from_pretrained("google/timesfm-3.0-pytorch", device=DISPOSITIVO, per_core_batch_size=lote)

    def f(ctx):
        outs = list(fc.predict_batch(contexts=list(ctx), horizon=H, return_quantiles=True))
        q = np.stack([_np(o.quantiles) for o in outs])  # [B, H, 9]
        return q[:, :, 4], q[:, :, 0], q[:, :, 8]

    return lambda c: _por_lotes(f, c, 2048)


def tirex2(H, lote=256):
    from tirex2 import TimeseriesType, load_model

    m = load_model("NX-AI/TiRex-2", device=DISPOSITIVO)

    def f(ctx):
        ts = [TimeseriesType(target=torch.as_tensor(c)[None, :], past_covariates=None, future_covariates=None)
              for c in ctx]
        out = m.forecast(ts, prediction_length=H, output_type="numpy")
        q = np.stack([np.asarray(o)[0] for o in out])  # [B, 9, H]
        return q[:, 4], q[:, 0], q[:, 8]

    return lambda c: _por_lotes(f, c, lote)


def timestral(H, lote=128):
    from timestral import TimestralForecaster

    fc = TimestralForecaster.from_pretrained("mistralai/Timestral-209M", device=DISPOSITIVO)

    def f(ctx):
        with torch.inference_mode():
            p = fc.forecast(torch.as_tensor(ctx)[:, None, :], prediction_length=H)
            return _np(p.median)[:, 0], _np(p.quantile(0.1))[:, 0], _np(p.quantile(0.9))[:, 0]

    return lambda c: _por_lotes(f, c, lote)


def simons(H, lote=128):
    from simons import Simons

    m = Simons.from_pretrained("abel-lab/Simons-297M", device=DISPOSITIVO)

    def f(ctx):
        with torch.inference_mode():
            q = _np(m.forecast(torch.as_tensor(ctx), horizon=H))  # [B, H, 9]
        return q[:, :, 4], q[:, :, 0], q[:, :, 8]

    return lambda c: _por_lotes(f, c, lote)


def t0(H, lote=128):
    from t0 import T0Forecaster

    m = T0Forecaster.from_pretrained("theforecastingcompany/t0-gamma").to(DISPOSITIVO).eval()

    def f(ctx):
        with torch.inference_mode():
            o = m.predict(torch.as_tensor(ctx, device=DISPOSITIVO), horizon=H, quantile_levels=[0.1, 0.5, 0.9])
        q = _np(o.quantiles)
        return q[:, :, 1], q[:, :, 0], q[:, :, 2]

    return lambda c: _por_lotes(f, c, lote)


def toto2(H, lote=128):
    from toto2 import Toto2Model

    m = Toto2Model.from_pretrained("Datadog/Toto-2.0-313m").to(DISPOSITIVO).eval()

    def f(ctx):
        y = torch.as_tensor(ctx, device=DISPOSITIVO)[:, None, :]
        with torch.inference_mode():
            q = m.forecast({"target": y, "target_mask": torch.ones_like(y, dtype=torch.bool),
                            "series_ids": torch.zeros(y.shape[0], 1, dtype=torch.long, device=DISPOSITIVO)},
                           horizon=H, decode_block_size=None, has_missing_values=False)
        q = _np(q)[:, :, 0]  # [9, B, H]
        return q[4], q[0], q[8]

    return lambda c: _por_lotes(f, c, lote)


MODELOS = {"chronos2": chronos2, "timesfm25": timesfm25, "timesfm3": timesfm3, "tirex2": tirex2,
           "timestral": timestral, "simons": simons, "t0": t0, "toto2": toto2}


def cargar(modelo, H):
    return MODELOS[modelo](H)
