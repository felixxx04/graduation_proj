package com.medical.dto.response;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class UserDto {
    private Long id;
    private String username;
    private String role;
    private String status;
    private LocalDateTime lastLoginAt;
}
