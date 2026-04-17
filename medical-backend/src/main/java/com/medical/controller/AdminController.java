package com.medical.controller;

import com.medical.dto.request.StatusUpdateRequest;
import com.medical.dto.request.TrainingStartRequest;
import com.medical.dto.response.ApiResponse;
import com.medical.dto.response.EpochDto;
import com.medical.dto.response.TrainingRunDto;
import com.medical.dto.response.UserDto;
import com.medical.entity.User;
import com.medical.service.AdminService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {
    private final AdminService adminService;

    @GetMapping("/users")
    public ApiResponse<List<UserDto>> getUsers(@RequestAttribute String username) {
        List<UserDto> dtos = adminService.getAllUsers().stream()
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
        User user = adminService.updateUserStatus(id, request.getEnabled());
        return ApiResponse.success(toDto(user));
    }

    @GetMapping("/training/history")
    public ApiResponse<List<TrainingRunDto>> getTrainingHistory(
        @RequestParam(defaultValue = "10") int limit,
        @RequestAttribute String username
    ) {
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
        Map<String, Object> result = adminService.startTraining(request.getEpochs());

        TrainingRunDto run = new TrainingRunDto();
        run.setId(Long.valueOf(result.get("id").toString()));
        run.setStatus((String) result.get("status"));
        run.setTotalEpochs(((Number) result.get("totalEpochs")).intValue());
        run.setEpsilonPerEpoch(((Number) result.get("epsilonPerEpoch")).doubleValue());
        run.setStartedAt(LocalDateTime.now().minusMinutes(request.getEpochs()).toString());
        run.setFinishedAt(LocalDateTime.now().toString());

        List<EpochDto> epochList = new ArrayList<>();
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> epochsData = (List<Map<String, Object>>) result.get("epochs");
        if (epochsData != null) {
            for (Map<String, Object> e : epochsData) {
                EpochDto epoch = new EpochDto();
                epoch.setEpochIndex(((Number) e.get("epochIndex")).intValue());
                epoch.setLoss(((Number) e.get("loss")).doubleValue());
                epoch.setAccuracy(((Number) e.get("accuracy")).doubleValue());
                epoch.setEpsilonSpent(((Number) e.get("epsilonSpent")).doubleValue());
                epoch.setCreatedAt(LocalDateTime.now().toString());
                epochList.add(epoch);
            }
        }
        run.setEpochs(epochList);

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
}
