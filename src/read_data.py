import pandas as pd

# Liest das Blatt 'Gesamt' aus der Excel-Mappe der Kollegen
df = pd.read_excel("excel/praxis_uebung.xlsx", sheet_name="Gesamt")
print("Geladene Daten:")
print(df.head())