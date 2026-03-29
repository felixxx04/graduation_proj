package com.medical.entity;

import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class Patient {
    private Long id;
    private String name;
    private String gender;
    private LocalDate birthDate;
    private String phone;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
