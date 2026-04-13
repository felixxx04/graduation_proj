package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.entity.User;
import com.medical.repository.UserRepository;
import com.medical.service.AuthService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {
    private final UserRepository userRepository;
    private final AuthService authService;

    @GetMapping("/users")
    public ApiResponse<List<UserDto>> getUsers(@RequestAttribute String username) {
        List<User> users = userRepository.findAll();
        List<UserDto> dtos = users.stream()
            .map(this::toDto)
            .collect(Collectors.toList());
        return ApiResponse.success(dtos);
    }

    @PatchMapping("/users/{id}/status")
    public ApiResponse<UserDto> updateUserStatus(
        @PathVariable Long id,
        @RequestBody StatusUpdateRequest request,
        @RequestAttribute String username
    ) {
        User user = userRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("用户不存在"));

        user.setEnabled(request.getEnabled());
        user.setUpdatedAt(LocalDateTime.now());
        userRepository.update(user);

        return ApiResponse.success(toDto(user));
    }

    @GetMapping("/training/history")
    public ApiResponse<List<TrainingRunDto>> getTrainingHistory(
        @RequestParam(defaultValue = "10") int limit,
        @RequestAttribute String username
    ) {
        // 返回模拟的训练历史数据
        List<TrainingRunDto> runs = new ArrayList<>();
        for (int i = 1; i <= Math.min(limit, 3); i++) {
            TrainingRunDto run = new TrainingRunDto();
            run.setId((long) i);
            run.setStatus("COMPLETED");
            run.setTotalEpochs(10);
            run.setEpsilonPerEpoch(0.1);
            run.setStartedAt(LocalDateTime.now().minusDays(i).toString());
            run.setFinishedAt(LocalDateTime.now().minusDays(i).plusMinutes(5).toString());
            run.setEpochs(generateMockEpochs(10));
            runs.add(run);
        }
        return ApiResponse.success(runs);
    }

    @PostMapping("/training/start")
    public ApiResponse<TrainingRunDto> startTraining(
        @RequestBody TrainingStartRequest request,
        @RequestAttribute String username
    ) {
        // 返回模拟的新训练任务
        TrainingRunDto run = new TrainingRunDto();
        run.setId(System.currentTimeMillis());
        run.setStatus("RUNNING");
        run.setTotalEpochs(request.getEpochs());
        run.setEpsilonPerEpoch(0.1);
        run.setStartedAt(LocalDateTime.now().toString());
        run.setFinishedAt(null);
        run.setEpochs(new ArrayList<>());
        return ApiResponse.success(run);
    }

    private List<EpochDto> generateMockEpochs(int count) {
        List<EpochDto> epochs = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            EpochDto epoch = new EpochDto();
            epoch.setEpochIndex(i);
            epoch.setLoss(0.5 - i * 0.03 + Math.random() * 0.05);
            epoch.setAccuracy(0.8 + i * 0.015 + Math.random() * 0.02);
            epoch.setEpsilonSpent(0.1);
            epoch.setCreatedAt(LocalDateTime.now().minusMinutes(count - i).toString());
            epochs.add(epoch);
        }
        return epochs;
    }

    private UserDto toDto(User user) {
        UserDto dto = new UserDto();
        dto.setId(user.getId());
        dto.setUsername(user.getUsername());
        dto.setRole(user.getRole());
        dto.setStatus(user.getEnabled() != null && user.getEnabled() ? "ACTIVE" : "DISABLED");
        dto.setLastLoginAt(user.getUpdatedAt());
        return dto;
    }

    @Data
    public static class UserDto {
        private Long id;
        private String username;
        private String role;
        private String status;
        private LocalDateTime lastLoginAt;
    }

    @Data
    public static class StatusUpdateRequest {
        private String status;

        public Boolean getEnabled() {
            return "ACTIVE".equals(status);
        }
    }

    @Data
    public static class TrainingRunDto {
        private Long id;
        private String status;
        private int totalEpochs;
        private double epsilonPerEpoch;
        private String startedAt;
        private String finishedAt;
        private List<EpochDto> epochs;
    }

    @Data
    public static class EpochDto {
        private int epochIndex;
        private double loss;
        private double accuracy;
        private double epsilonSpent;
        private String createdAt;
    }

    @Data
    public static class TrainingStartRequest {
        private int epochs;
    }
}
