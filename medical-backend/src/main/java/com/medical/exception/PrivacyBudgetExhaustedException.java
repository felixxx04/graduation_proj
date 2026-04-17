package com.medical.exception;

import org.springframework.http.HttpStatus;

public class PrivacyBudgetExhaustedException extends BusinessException {
    public PrivacyBudgetExhaustedException(String message) {
        super(message, HttpStatus.BAD_REQUEST);
    }
}
