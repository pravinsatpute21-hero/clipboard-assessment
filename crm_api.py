import requests
import pandas as pd

BASE_URL = "https://analyst-assessment-production.up.railway.app/api/v1"
API_TOKEN = "bh_A5lLIu7eIB6Wemk4Ju4pXA"

headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}


def get_all_accounts():
    """Pull all accounts from CRM"""
    all_accounts = []
    page = 1

    while True:
        print(f"Fetching CRM page {page}...")
        response = requests.get(
            f"{BASE_URL}/accounts",
            headers=headers,
            params={"page": page, "per_page": 50}
        )

        data = response.json()
        print(f"Response keys: {data.keys()}")

        # Get accounts from response
        accounts = data.get('accounts', data.get('data', data.get('results', [])))

        if not accounts:
            break

        all_accounts.extend(accounts)

        # Check if more pages
        total = data.get('total', 0)
        if len(all_accounts) >= total or len(accounts) == 0:
            break

        page += 1

    return all_accounts


if __name__ == "__main__":
    print("Pulling CRM accounts...")
    accounts = get_all_accounts()

    df = pd.DataFrame(accounts)
    df.to_csv('crm_accounts.csv', index=False)

    print(f"\nDone! Found {len(accounts)} CRM accounts")
    print(f"Columns: {df.columns.tolist()}")
    print(df.head(10).to_string())