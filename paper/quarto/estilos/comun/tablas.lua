-- Tablas flotantes para los estilos en PDF.
--
-- Pandoc escribe las tablas como longtable: no la admite LaTeX a dos columnas (IEEE) y, a una columna, parte
-- las tablas cortas entre páginas. Este filtro las reescribe como un tabular dentro de un flotante, con
-- columnas p que respetan los anchos relativos de `tbl-colwidths` y permiten cortar con guion también la
-- primera palabra de cada celda. Quarto pone el título y la etiqueta, así que las referencias cruzadas siguen
-- funcionando. Cada perfil elige, en su formato:
--   tablas-entorno: table (por defecto) o table* (a lo ancho de la página, para dos columnas)
--   tablas-letra:   small (por defecto), footnotesize, etc.

local function celda(cell)
  local latex = pandoc.write(pandoc.Pandoc(cell.contents), "latex")
  return (latex:gsub("%s+$", ""))
end

local function fila(row)
  local celdas = {}
  for _, cell in ipairs(row.cells) do
    table.insert(celdas, celda(cell))
  end
  return table.concat(celdas, " & ") .. " \\\\"
end

local function alineacion(align)
  if align == "AlignRight" then
    return "\\raggedleft"
  elseif align == "AlignCenter" then
    return "\\centering"
  end
  return "\\raggedright"
end

-- Anchos relativos: los de tbl-colwidths (en porcentajes) si están; si no, los de pandoc; si no, iguales.
local function anchos(tbl, atributo)
  local n = #tbl.colspecs
  local w = {}
  if atributo then
    for numero in atributo:gmatch("[%d%.]+") do
      table.insert(w, tonumber(numero))
    end
  end
  if #w ~= n then
    w = {}
    for i, spec in ipairs(tbl.colspecs) do
      w[i] = tonumber(spec[2]) or 0
    end
  end
  local total = 0
  for _, x in ipairs(w) do
    total = total + x
  end
  for i = 1, n do
    w[i] = total > 0 and w[i] / total or 1 / n
  end
  return w
end

local entorno = "table"
local letra = "small"

local function tabular(tbl, atributo)
  local w = anchos(tbl, atributo)
  local columnas = {}
  for i, spec in ipairs(tbl.colspecs) do
    table.insert(columnas, string.format(
      ">{%s\\arraybackslash\\hspace{0pt}}p{\\dimexpr %.4f\\linewidth-2\\tabcolsep\\relax}", alineacion(spec[1]), w[i]))
  end
  -- Quarto envuelve el contenido en un table con su título; para table* lo reconoce si viene envuelto.
  local lineas = {}
  if entorno ~= "table" then
    table.insert(lineas, "\\begin{" .. entorno .. "}")
  end
  for _, linea in ipairs({
    "\\" .. letra,
    "\\begin{tabular}{@{}" .. table.concat(columnas) .. "@{}}",
    "\\toprule",
  }) do
    table.insert(lineas, linea)
  end
  for _, row in ipairs(tbl.head.rows) do
    table.insert(lineas, fila(row))
  end
  if #tbl.head.rows > 0 then
    table.insert(lineas, "\\midrule")
  end
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.head) do
      table.insert(lineas, fila(row))
    end
    for _, row in ipairs(body.body) do
      table.insert(lineas, fila(row))
    end
  end
  for _, row in ipairs(tbl.foot.rows) do
    table.insert(lineas, fila(row))
  end
  table.insert(lineas, "\\bottomrule")
  table.insert(lineas, "\\end{tabular}")
  if entorno ~= "table" then
    table.insert(lineas, "\\end{" .. entorno .. "}")
  end
  return pandoc.RawBlock("latex", table.concat(lineas, "\n"))
end

if not quarto.doc.is_format("latex") then
  return {}
end

return {
  {
    Meta = function(meta)
      if meta["tablas-entorno"] then
        entorno = pandoc.utils.stringify(meta["tablas-entorno"])
      end
      if meta["tablas-letra"] then
        letra = pandoc.utils.stringify(meta["tablas-letra"])
      end
    end,
  },
  {
    FloatRefTarget = function(float)
      if float.type ~= "Table" then
        return nil
      end
      local atributo = float.attributes["tbl-colwidths"]
      local function convertir(tbl)
        return tabular(tbl, atributo or tbl.attributes["tbl-colwidths"])
      end
      if float.content.t == "Table" then
        float.content = convertir(float.content)
      else
        float.content = pandoc.Div(quarto.utils.as_blocks(float.content)):walk({ Table = convertir }).content
      end
      return float
    end,
  },
}
