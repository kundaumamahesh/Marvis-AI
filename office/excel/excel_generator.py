from openpyxl import Workbook
import csv
from io import StringIO
import os


class ExcelGenerator:

    async def generate(
        self,
        csv_data,
        output_path
    ):

        os.makedirs(
            os.path.dirname(output_path),
            exist_ok=True
        )

        wb = Workbook()
        ws = wb.active

        reader = csv.reader(
            StringIO(csv_data)
        )

        for row in reader:
            ws.append(row)

        wb.save(output_path)

        return output_path
