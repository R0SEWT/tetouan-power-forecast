-- Bloque de autores para IEEEtran (conference) con varios autores: un bloque por autor, con el nombre sobre su
-- correo, en filas de tres, y la afiliación común en una línea debajo. Lee los autores del YAML de
-- short-paper.qmd en su orden y deja el LaTeX en la variable `autores-ieee`, que usa estilos/title.tex.

local POR_FILA = 3

local function latex(valor)
  if valor == nil then
    return ""
  end
  if type(valor) == "table" and valor.literal ~= nil then
    valor = valor.literal
  end
  local texto = pandoc.utils.stringify(valor)
  local escrito = pandoc.write(pandoc.Pandoc({ pandoc.Plain({ pandoc.Str(texto) }) }), "latex")
  return (escrito:gsub("%s+$", ""))
end

local function afiliacion(meta)
  local lista = meta["by-affiliation"] or meta["affiliations"]
  if lista == nil or #lista == 0 then
    return nil
  end
  local a = lista[1]
  local partes = { "\\textit{" .. latex(a.name) .. "}" }
  for _, campo in ipairs({ "city", "country" }) do
    if a[campo] ~= nil then
      table.insert(partes, latex(a[campo]))
    end
  end
  return table.concat(partes, ", ")
end

if not quarto.doc.is_format("latex") then
  return {}
end

return {
  {
    Meta = function(meta)
      local autores = meta["by-author"] or meta["author"]
      if autores == nil then
        return nil
      end
      local bloques = {}
      for i, autor in ipairs(autores) do
        local bloque = "\\IEEEauthorblockN{\\normalsize " .. latex(autor.name) .. "}"
        if autor.email ~= nil then
          bloque = bloque .. "\n\\IEEEauthorblockA{\\small " .. latex(autor.email) .. "}"
        end
        if i > 1 then
          table.insert(bloques, (i - 1) % POR_FILA == 0 and "\\linebreakand" or "\\and")
        end
        table.insert(bloques, bloque)
      end
      local comun = afiliacion(meta)
      if comun ~= nil then
        table.insert(bloques, "\\linebreakand")
        table.insert(bloques, "\\IEEEauthorblockA{" .. comun .. "}")
      end
      meta["autores-ieee"] = pandoc.RawInline("latex", table.concat(bloques, "\n"))
      return meta
    end,
  },
}
