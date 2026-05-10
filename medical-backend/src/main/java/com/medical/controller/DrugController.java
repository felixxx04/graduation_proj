package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.entity.Drug;
import com.medical.service.DrugService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/drugs")
@RequiredArgsConstructor
public class DrugController {
    private final DrugService drugService;
    
    @GetMapping
    public ApiResponse<List<Drug>> getAllDrugs() {
        return ApiResponse.success(drugService.getAllDrugs());
    }
    
    @GetMapping("/{id}")
    public ApiResponse<Drug> getDrugById(@PathVariable Long id) {
        return ApiResponse.success(drugService.getDrugById(id));
    }
    
    @GetMapping("/category/{category}")
    public ApiResponse<List<Drug>> getDrugsByCategory(@PathVariable String category) {
        return ApiResponse.success(drugService.getDrugsByCategory(category));
    }

    @GetMapping("/database")
    public ApiResponse<List<Drug>> getDrugDatabase(
            @RequestParam(required = false) String search,
            @RequestParam(required = false) String category) {
        if (search != null && !search.isBlank()) {
            return ApiResponse.success(drugService.searchDrugs(search));
        }
        if (category != null && !category.isBlank()) {
            return ApiResponse.success(drugService.getDrugsByCategory(category));
        }
        return ApiResponse.success(drugService.getAllDrugs());
    }
}
