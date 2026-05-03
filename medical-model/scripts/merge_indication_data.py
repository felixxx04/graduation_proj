"""Merge indication_map into merged_drugs to fix inference-time matching gaps.

Problem: merged_drugs and indication_map have INCONSISTENT indications.
Training uses indication_map (rich), inference uses merged_drugs (sparse).
This script enriches merged_drugs with missing indications from indication_map.
"""
import json, logging, sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def merge_indications(data_path: str):
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    merged_drugs = data.get('merged_drugs', {})
    indication_map = data.get('indication_map', {})

    added_total = 0
    drugs_enriched = 0
    drugs_unchanged = 0

    for drug_key, drug in merged_drugs.items():
        drug_name = drug.get('generic_name', drug_key)
        existing_conditions = set()
        for ind in drug.get('indications', []):
            if isinstance(ind, dict):
                existing_conditions.add(ind.get('condition', '').lower())

        # Look up in indication_map
        im_entry = indication_map.get(drug_name)
        if not im_entry:
            # Try case-insensitive match
            im_entry = None
            lower_name = drug_name.lower()
            for k in indication_map:
                if k.lower() == lower_name:
                    im_entry = indication_map[k]
                    break

        if im_entry:
            new_inds = []
            for ind in im_entry:
                cond = str(ind.get('condition', ind) if isinstance(ind, dict) else ind)
                if cond.lower() not in existing_conditions:
                    new_inds.append({'condition': cond, 'type': ind.get('type', 'On Label')})

            if new_inds:
                drug['indications'] = list(drug.get('indications', [])) + new_inds
                added_total += len(new_inds)
                drugs_enriched += 1
            else:
                drugs_unchanged += 1
        else:
            drugs_unchanged += 1

    data['merged_drugs'] = merged_drugs

    # Write back
    backup_path = data_path.replace('.json', '_backup.json')
    import shutil
    shutil.copy2(data_path, backup_path)
    logger.info(f'Backup saved to {backup_path}')

    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f'Drugs enriched: {drugs_enriched}/{len(merged_drugs)} ({drugs_enriched/len(merged_drugs)*100:.1f}%)')
    logger.info(f'New indications added: {added_total}')
    logger.info(f'Total indications (after merge): {sum(len(d.get("indications",[])) for d in merged_drugs.values())}')


if __name__ == '__main__':
    data_path = sys.argv[1] if len(sys.argv) > 1 else 'data/pipeline_data.json'
    merge_indications(data_path)
    logger.info('Done!')
