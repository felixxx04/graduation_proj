package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.service.AuthService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {
    private final AuthService authService;
    
    @PostMapping("/login")
    public ApiResponse<Map<String, Object>> login(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String password = request.get("password");
        try {
            Map<String, Object> result = authService.login(username, password);
            return ApiResponse.success("登录成功", result);
        } catch (RuntimeException e) {
            return ApiResponse.error(e.getMessage());
        }
    }
    
    @GetMapping("/me")
    public ApiResponse<Map<String, Object>> getCurrentUser(@RequestAttribute String username) {
        var user = authService.getCurrentUser(username);
        if (user == null) {
            return ApiResponse.error("用户不存在");
        }
        return ApiResponse.success(Map.of(
            "id", user.getId(),
            "username", user.getUsername(),
            "role", user.getRole()
        ));
    }
}
