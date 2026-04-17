package com.medical.service;

import com.medical.entity.Drug;
import com.medical.exception.ResourceNotFoundException;
import com.medical.repository.DrugRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
@RequiredArgsConstructor
public class DrugService {
    private final DrugRepository drugRepository;
    
    public List<Drug> getAllDrugs() {
        return drugRepository.findAll();
    }
    
    public Drug getDrugById(Long id) {
        Drug drug = drugRepository.findById(id);
        if (drug == null) {
            throw new ResourceNotFoundException("药物不存在: id=" + id);
        }
        return drug;
    }
    
    public List<Drug> getDrugsByCategory(String category) {
        return drugRepository.findByCategory(category);
    }
}
