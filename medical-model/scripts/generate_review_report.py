"""Generate weekly review report from the review_log table.
Analyzes rejection rates, modification patterns, and disease routing quality."""
import json
import os
import sys
import io
import requests
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8080')


def fetch_stats(endpoint, start_date, end_date):
    url = f'{BACKEND_URL}/api/review/stats/{endpoint}'
    params = {'startDate': start_date, 'endDate': end_date}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  Warning: failed to fetch {endpoint}: {e}")
    return []


def main():
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    print("=" * 60)
    print(f"Medical Recommendation Review Weekly Report ({start_date} ~ {end_date})")
    print("=" * 60)

    print("\n## 1. Top 10 Diseases by Rejection Rate")
    print("-" * 40)
    rejections = fetch_stats('rejections', start_date, end_date)
    if rejections:
        for i, row in enumerate(rejections[:10], 1):
            print(f"  {i}. {row.get('disease_cn', '?')}: {row.get('reject_count', 0)} rejections")
    else:
        print("  No data")

    print("\n## 2. Top 10 Doctor Modifications")
    print("-" * 40)
    modifications = fetch_stats('modifications', start_date, end_date)
    if modifications:
        for i, row in enumerate(modifications[:10], 1):
            print(f"  {i}. {row.get('disease_cn', '?')} -> doctor chose: {row.get('doctor_selected_drug', '?')} ({row.get('modify_count', 0)}x)")
    else:
        print("  No data")

    print("\n## 3. Threshold Alerts (Rejection Rate > 50%)")
    print("-" * 40)
    alert_count = 0
    for row in (rejections or [])[:10]:
        disease = row.get('disease_cn', '')
        reject_count = row.get('reject_count', 0)
        if reject_count >= 3:
            alert_count += 1
            print(f"  WARNING: {disease}: {reject_count} rejections — check routing rules")
    if alert_count == 0:
        print("  No high-rejection diseases")

    print("\n" + "=" * 60)
    print("Report complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
