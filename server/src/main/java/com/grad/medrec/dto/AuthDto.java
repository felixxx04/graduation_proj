package com.grad.medrec.dto;

import jakarta.validation.constraints.NotBlank;

public final class AuthDto {

    private AuthDto() {
    }

    public record LoginRequest(
            @NotBlank String username,
            @NotBlank String password
    ) {
    }

    public record UserInfo(
            Long id,
            String username,
            String role,
            String status
    ) {
    }

    public record LoginResponse(
            String token,
            UserInfo user
    ) {
    }
}
