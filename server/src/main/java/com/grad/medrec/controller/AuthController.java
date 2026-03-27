package com.grad.medrec.controller;

import com.grad.medrec.dto.ApiResponse;
import com.grad.medrec.dto.AuthDto;
import com.grad.medrec.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ApiResponse<AuthDto.LoginResponse> login(@Valid @RequestBody AuthDto.LoginRequest request) {
        return ApiResponse.ok(authService.login(request));
    }

    @GetMapping("/me")
    public ApiResponse<AuthDto.UserInfo> me() {
        return ApiResponse.ok(authService.me());
    }
}
