import pandas as pd

BASE_URL = "http://localhost:8000/assets"

companies = {
    "Apple": f"{BASE_URL}/apple.png",
    "Microsoft": f"{BASE_URL}/microsoft.png",
    "Alphabet": f"{BASE_URL}/alphabet.png",
}

df = pd.DataFrame(
    [
        {"Company": company, "Logo": url}
        for company, url in companies.items()
    ]
)

df.to_csv(
    "data/processed/company_logos.csv",
    index=False
)

print(df)
print("Logo table created.")