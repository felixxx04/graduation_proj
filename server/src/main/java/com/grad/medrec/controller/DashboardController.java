package com.grad.medrec.controller;

import com.grad.medrec.dto.AdminDto;
import com.grad.medrec.dto.ApiResponse;
import com.grad.medrec.service.AdminService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {

    private final AdminService adminService;

    public DashboardController(AdminService adminService) {
        this.adminService = adminService;
    }

    @GetMapping("/visualization")
    public ApiResponse<AdminDto.DashboardResponse> visualization() {
        return ApiResponse.ok(adminService.dashboard());
    }
}
