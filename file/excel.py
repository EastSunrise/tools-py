import os

import xlwt


def write(data, dst, filename='example'):
    """
    Write the data to an excel file.
    :param data: data to write, three-dimensional array
    :param dst: destination directory of the created file
    :param filename: name of the file
    """
    wb = xlwt.Workbook()
    for key, value in data.items():
        sheet = wb.add_sheet(key)
        for r, line in enumerate(value):
            for c, cell in enumerate(line):
                sheet.write(r, c, xlwt.Formula(cell))
    wb.save(os.path.join(dst, filename + '.xls'))
