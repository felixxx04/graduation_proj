package com.medical.dto.response;

import lombok.Data;
import java.util.List;

@Data
public class TrainingRunDto {
    private Long id;
    private String status;
    private int totalEpochs;
    private double epsilonPerEpoch;
    private String startedAt;
    private String finishedAt;
    private List<EpochDto> epochs;
}
