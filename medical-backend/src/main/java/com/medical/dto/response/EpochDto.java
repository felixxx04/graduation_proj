package com.medical.dto.response;

import lombok.Data;

@Data
public class EpochDto {
    private int epochIndex;
    private double loss;
    private double accuracy;
    private double epsilonSpent;
    private String createdAt;
}
