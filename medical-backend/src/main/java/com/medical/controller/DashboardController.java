package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.service.AuthService;
import com.medical.service.DashboardService;
import com.medical.entity.User;
import com.medical.exception.ResourceNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
public class DashboardController {
    private final DashboardService dashboardService;
    private final AuthService authService;

    @GetMapping("/visualization")
    public ApiResponse<Map<String, Object>> getVisualization(@RequestAttribute String username) {
        User user = authService.getCurrentUser(username);
        if (user == null) {
            throw new ResourceNotFoundException("用户不存在: " + username);
        }
        return ApiResponse.success(dashboardService.getVisualization(user.getId()));
    }
}
