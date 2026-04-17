package com.medical.controller;

import com.medical.dto.request.PrivacyConfigRequest;
import com.medical.dto.response.ApiResponse;
import com.medical.entity.PrivacyConfig;
import com.medical.service.PrivacyService;
import com.medical.service.AuthService;
import com.medical.entity.User;
import com.medical.exception.ResourceNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/privacy")
@RequiredArgsConstructor
public class PrivacyController {
    private final PrivacyService privacyService;
    private final AuthService authService;

    private Long getUserId(String username) {
        User user = authService.getCurrentUser(username);
        if (user == null) {
            throw new ResourceNotFoundException("用户不存在: " + username);
        }
        return user.getId();
    }

    @GetMapping("/config")
    public ApiResponse<PrivacyConfig> getConfig(@RequestAttribute String username) {
        return ApiResponse.success(privacyService.getConfig(getUserId(username)));
    }

    @PutMapping("/config")
    public ApiResponse<PrivacyConfig> updateConfig(@RequestAttribute String username, @RequestBody PrivacyConfigRequest request) {
        return ApiResponse.success("更新成功", privacyService.updateConfig(getUserId(username), request));
    }

    @GetMapping("/budget")
    public ApiResponse<Map<String, Object>> getBudget(@RequestAttribute String username) {
        return ApiResponse.success(privacyService.getBudget(getUserId(username)));
    }

    @GetMapping("/events")
    public ApiResponse<List<Map<String, Object>>> getEvents(@RequestAttribute String username,
                                                            @RequestParam(defaultValue = "30") int limit) {
        return ApiResponse.success(privacyService.getLedgerEvents(getUserId(username), limit));
    }

    @DeleteMapping("/events")
    public ApiResponse<Void> clearEvents(@RequestAttribute String username) {
        privacyService.clearLedger(getUserId(username));
        return ApiResponse.success("账本已清空", null);
    }
}
