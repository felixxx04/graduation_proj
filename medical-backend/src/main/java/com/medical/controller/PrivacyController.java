package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.entity.PrivacyConfig;
import com.medical.service.PrivacyService;
import com.medical.service.AuthService;
import com.medical.entity.User;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/privacy")
@RequiredArgsConstructor
public class PrivacyController {
    private final PrivacyService privacyService;
    private final AuthService authService;
    
    private Long getUserId(String username) {
        User user = authService.getCurrentUser(username);
        return user != null ? user.getId() : null;
    }
    
    @GetMapping("/config")
    public ApiResponse<PrivacyConfig> getConfig(@RequestAttribute String username) {
        Long userId = getUserId(username);
        if (userId == null) {
            return ApiResponse.error("用户不存在");
        }
        PrivacyConfig config = privacyService.getConfig(userId);
        if (config == null) {
            return ApiResponse.error("隐私配置不存在");
        }
        return ApiResponse.success(config);
    }
    
    @PutMapping("/config")
    public ApiResponse<PrivacyConfig> updateConfig(@RequestAttribute String username, @RequestBody PrivacyConfig config) {
        Long userId = getUserId(username);
        if (userId == null) {
            return ApiResponse.error("用户不存在");
        }
        PrivacyConfig updated = privacyService.updateConfig(userId, config);
        return ApiResponse.success("更新成功", updated);
    }
    
    @GetMapping("/budget")
    public ApiResponse<Map<String, Object>> getBudget(@RequestAttribute String username) {
        Long userId = getUserId(username);
        if (userId == null) {
            return ApiResponse.error("用户不存在");
        }
        Map<String, Object> budget = privacyService.getBudget(userId);
        if (budget == null) {
            return ApiResponse.error("隐私配置不存在");
        }
        return ApiResponse.success(budget);
    }
}
