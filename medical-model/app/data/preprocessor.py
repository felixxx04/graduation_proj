import numpy as np
from typing import Dict, List, Any
import json

class PatientFeatureProcessor:
    def __init__(self):
        self.age_bins = [0, 18, 30, 45, 60, 75, 100]
        self.disease_vocab = {}
        self.drug_vocab = {}
        self.allergy_vocab = {}
        
    def fit(self, patients: List[Dict[str, Any]], drugs: List[Dict[str, Any]]):
        diseases = set()
        for p in patients:
            if 'chronic_diseases' in p:
                if isinstance(p['chronic_diseases'], str):
                    diseases.update(json.loads(p['chronic_diseases']))
                else:
                    diseases.update(p['chronic_diseases'])
        self.disease_vocab = {d: i for i, d in enumerate(sorted(diseases))}
        
        drug_names = set()
        for d in drugs:
            drug_names.add(d['name'])
        self.drug_vocab = {d: i for i, d in enumerate(sorted(drug_names))}
        
        allergies = set()
        for p in patients:
            if 'allergies' in p:
                if isinstance(p['allergies'], str):
                    allergies.update(json.loads(p['allergies']))
                else:
                    allergies.update(p['allergies'])
        self.allergy_vocab = {a: i for i, a in enumerate(sorted(allergies)) if a != '无'}
        
    def transform_patient(self, patient: Dict[str, Any]) -> np.ndarray:
        features = []
        
        age = patient.get('age', 45)
        age_bin = np.digitize([age], self.age_bins)[0]
        age_onehot = np.zeros(len(self.age_bins))
        age_onehot[age_bin] = 1
        features.extend(age_onehot)
        
        gender = patient.get('gender', '男')
        features.append(1 if gender == '男' else 0)
        
        diseases = patient.get('chronic_diseases', [])
        if isinstance(diseases, str):
            diseases = json.loads(diseases) if diseases else []
        disease_vec = np.zeros(len(self.disease_vocab))
        for d in diseases:
            if d in self.disease_vocab:
                disease_vec[self.disease_vocab[d]] = 1
        features.extend(disease_vec)
        
        allergies = patient.get('allergies', [])
        if isinstance(allergies, str):
            allergies = json.loads(allergies) if allergies else []
        allergy_vec = np.zeros(len(self.allergy_vocab))
        for a in allergies:
            if a in self.allergy_vocab:
                allergy_vec[self.allergy_vocab[a]] = 1
        features.extend(allergy_vec)
        
        return np.array(features, dtype=np.float32)
    
    def transform_drug(self, drug: Dict[str, Any]) -> np.ndarray:
        features = []
        
        category = drug.get('category', '')
        category_map = {'降糖药': 0, '降压药': 1, '降脂药': 2, '抗血小板药': 3, 
                       '消化系统用药': 4, '心血管用药': 5, '抗感染药': 6, '其他': 7}
        cat_vec = np.zeros(len(category_map))
        cat_vec[category_map.get(category, 7)] = 1
        features.extend(cat_vec)
        
        indications = drug.get('indications', [])
        if isinstance(indications, str):
            indications = json.loads(indications) if indications else []
        for ind in indications[:5]:
            features.append(hash(ind) % 100 / 100.0)
        features.extend([0] * (5 - len(indications[:5])))
        
        return np.array(features, dtype=np.float32)

    def get_field_dims(self) -> List[int]:
        return [
            len(self.age_bins),
            2,
            len(self.disease_vocab),
            len(self.allergy_vocab)
        ]
