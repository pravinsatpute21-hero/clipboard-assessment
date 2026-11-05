import pandas as pd
from rapidfuzz import fuzz
import json

BELLHAVEN_PARENT_ID = "0015QAPLGS3FVYEEEM"
BELLHAVEN_PARENT_NAME = "Bellhaven Senior Living (Parent Account)"


def normalize_name(name):
    """Clean name for comparison"""
    if not name:
        return ""
    name = name.lower().strip()
    name = name.replace('&', 'and')
    name = name.replace('-', ' ')
    name = name.replace(',', '')
    name = name.replace('.', '')
    return ' '.join(name.split())


def match_communities(website_df, crm_df):
    """Match website communities to CRM accounts"""
    results = []

    # Get all Bellhaven CRM accounts
    bellhaven_crm = crm_df[
        crm_df['parent_id'] == BELLHAVEN_PARENT_ID
        ].copy()

    print(f"Website communities: {len(website_df)}")
    print(f"CRM Bellhaven accounts: {len(bellhaven_crm)}")
    print(f"Total CRM accounts: {len(crm_df)}")

    # Track which CRM accounts got matched
    matched_crm_ids = set()

    for _, web_row in website_df.iterrows():
        web_name = web_row['name']
        web_city = web_row['city']
        web_state = web_row['state']
        web_zip = str(web_row['zip'])

        best_match = None
        best_score = 0
        best_crm_row = None

        # Try to match against ALL CRM accounts
        for _, crm_row in crm_df.iterrows():
            crm_name = crm_row['name']
            crm_city = crm_row['billing_city']
            crm_state = crm_row['billing_state']
            crm_zip = str(crm_row['billing_zip'])

            # Name similarity score
            name_score = fuzz.token_sort_ratio(
                normalize_name(web_name),
                normalize_name(crm_name)
            )

            # Location match bonus
            location_score = 0
            if str(web_city).lower() == str(crm_city).lower():
                location_score += 30
            if str(web_state).lower() == str(crm_state).lower():
                location_score += 20
            if web_zip == crm_zip:
                location_score += 20

            total_score = name_score + location_score

            if total_score > best_score:
                best_score = total_score
                best_crm_row = crm_row

        # Classify the match
        if best_score >= 140:
            # Strong match
            crm_parent_id = best_crm_row['parent_id']

            if crm_parent_id == BELLHAVEN_PARENT_ID:
                # Check if name needs update
                if normalize_name(web_name) == normalize_name(best_crm_row['name']):
                    classification = "CONFIDENT_MATCH"
                    action = "No changes needed"
                else:
                    classification = "NAME_MISMATCH"
                    action = f"Update name from '{best_crm_row['name']}' to '{web_name}'"
            else:
                # Wrong parent
                classification = "WRONG_PARENT"
                action = f"Change parent from '{best_crm_row['parent_name']}' to Bellhaven"

        elif best_score >= 100:
            classification = "POSSIBLE_MATCH"
            action = "Review needed - partial match"
        else:
            classification = "NO_CRM_ACCOUNT"
            action = f"Create new CRM account for {web_name}"
            best_crm_row = None

        result = {
            'web_name': web_name,
            'web_city': web_city,
            'web_state': web_state,
            'web_zip': web_zip,
            'web_care': web_row['care_offerings'],
            'match_type': classification,
            'action': action,
            'crm_id': best_crm_row['account_id'] if best_crm_row is not None else '',
            'crm_name': best_crm_row['name'] if best_crm_row is not None else '',
            'crm_parent': best_crm_row['parent_name'] if best_crm_row is not None else '',
            'crm_city': best_crm_row['billing_city'] if best_crm_row is not None else '',
            'crm_status': best_crm_row['status'] if best_crm_row is not None else '',
            'lifetime_revenue': best_crm_row['lifetime_revenue'] if best_crm_row is not None else 0,
            'outstanding_ar': best_crm_row['outstanding_ar'] if best_crm_row is not None else 0,
            'match_score': best_score,
        }

        if best_crm_row is not None:
            matched_crm_ids.add(best_crm_row['account_id'])

        results.append(result)

    # Find orphaned CRM accounts
    # Bellhaven CRM accounts not matched to any website community
    for _, crm_row in bellhaven_crm.iterrows():
        if crm_row['account_id'] not in matched_crm_ids:
            results.append({
                'web_name': '',
                'web_city': '',
                'web_state': '',
                'web_zip': '',
                'web_care': '',
                'match_type': 'ORPHAN_CRM',
                'action': f"Account exists in CRM under Bellhaven but not on website - mark Inactive",
                'crm_id': crm_row['account_id'],
                'crm_name': crm_row['name'],
                'crm_parent': crm_row['parent_name'],
                'crm_city': crm_row['billing_city'],
                'crm_status': crm_row['status'],
                'lifetime_revenue': crm_row['lifetime_revenue'],
                'outstanding_ar': crm_row['outstanding_ar'],
                'match_score': 0,
            })

    return pd.DataFrame(results)


if __name__ == "__main__":
    # Load data
    website_df = pd.read_csv('website_communities.csv')
    crm_df = pd.read_csv('crm_accounts.csv')

    print("Running matching logic...")
    results = match_communities(website_df, crm_df)

    results.to_csv('match_results.csv', index=False)

    print(f"\nMatch Results Summary:")
    print(results['match_type'].value_counts())
    print("\nDetailed Results:")
    print(results[['web_name', 'crm_name', 'match_type', 'action']].to_string())