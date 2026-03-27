package com.grad.medrec.controller;

import com.grad.medrec.dto.AdminDto;
import com.grad.medrec.dto.ApiResponse;
import com.grad.medrec.service.AdminService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private final AdminService adminService;

    public AdminController(AdminService adminService) {
        this.adminService = adminService;
    }

    @GetMapping("/users")
    public ApiResponse<List<AdminDto.UserItem>> users() {
        return ApiResponse.ok(adminService.listUsers());
    }

    @PatchMapping("/users/{id}/status")
    public ApiResponse<AdminDto.UserItem> updateStatus(@PathVariable Long id, @RequestBody AdminDto.UpdateUserStatusRequest request) {
        return ApiResponse.ok("updated", adminService.updateUserStatus(id, request));
    }

    @PostMapping("/training/start")
    public ApiResponse<AdminDto.TrainingRunItem> startTraining(@Valid @RequestBody AdminDto.StartTrainingRequest request) {
        return ApiResponse.ok(adminService.startTraining(request));
    }

    @GetMapping("/training/history")
    public ApiResponse<List<AdminDto.TrainingRunItem>> history(@RequestParam(defaultValue = "10") int limit) {
        return ApiResponse.ok(adminService.trainingHistory(limit));
    }
}
