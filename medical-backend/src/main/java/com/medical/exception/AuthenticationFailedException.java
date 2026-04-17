package com.medical.exception;

import org.springframework.http.HttpStatus;

public class AuthenticationFailedException extends BusinessException {
    public AuthenticationFailedException(String message) {
        super(message, HttpStatus.UNAUTHORIZED);
    }
}
