# -*- coding: utf-8 -*-
"""
Convierte cada hoja de los .xlsx de una carpeta en un CSV limpio.

  python scripts/xlsx_a_csv.py prueba_gebhardt

Salida: <carpeta>/csv/<prefijo>_<hoja>.csv (UTF-8, separador ',').

Hojas de datos: se descartan las filas de titulo previas al encabezado, los
encabezados repetidos dentro de la tabla, las filas vacias y las columnas sin
ningun valor. Hojas descriptivas (Legend, Description): una linea de texto por
fila, en una columna 'texto'.

Requiere openpyxl (el resto del proyecto usa solo la biblioteca estandar).
"""
import csv, os, re, sys
import openpyxl

HEADER_FIRST_CELL = {"Number", "Gene name"}


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s.replace("∆", "delta")).strip("_")


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)          # sin perder precision (p-valores, odds ratios)
    return str(v).strip()


def convert(folder):
    out = os.path.join(folder, "csv")
    os.makedirs(out, exist_ok=True)
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".xlsx") or fn.startswith("~$"):
            continue
        m = re.search(r"\.(sd\d+)", fn)
        prefix = m.group(1) if m else slug(os.path.splitext(fn)[0])
        wb = openpyxl.load_workbook(os.path.join(folder, fn), read_only=True, data_only=True)
        for ws in wb.worksheets:
            rows = [[fmt(v) for v in r] for r in ws.iter_rows(values_only=True)]
            hi = next((i for i, r in enumerate(rows) if r and r[0] in HEADER_FIRST_CELL), None)
            path = os.path.join(out, "%s_%s.csv" % (prefix, slug(ws.title)))
            if hi is None:      # hoja descriptiva
                data, header = [[" ".join(c for c in r if c)] for r in rows if any(r)], ["texto"]
            else:
                header = rows[hi]
                body = [r for r in rows[hi + 1:] if any(r) and r != header]
                ncol = max(i + 1 for r in [header] + body for i, c in enumerate(r) if c)
                header = header[:ncol]
                data = [r[:ncol] for r in body]
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(header)
                w.writerows(data)
            print("  %-60s %6d filas x %2d columnas" % (os.path.relpath(path, folder), len(data),
                                                      len(header)))


if __name__ == "__main__":
    convert(sys.argv[1] if len(sys.argv) > 1 else "prueba_gebhardt")
