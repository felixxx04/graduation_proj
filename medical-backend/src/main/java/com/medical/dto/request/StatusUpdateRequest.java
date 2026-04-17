package com.medical.dto.request;

import lombok.Data;

@Data
public class StatusUpdateRequest {
    private String status;

    public Boolean getEnabled() {
        return "ACTIVE".equals(status);
    }
}
