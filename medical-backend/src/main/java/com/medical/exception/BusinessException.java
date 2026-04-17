package com.medical.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

/**
 * 业务异常基类
 */
@Getter
public class BusinessException extends RuntimeException {
    private final HttpStatus status;

    public BusinessException(String message, HttpStatus status) {
        super(message);
        this.status = status;
    }

    public BusinessException(String message) {
        this(message, HttpStatus.BAD_REQUEST);
    }
}
