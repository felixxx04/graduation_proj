package com.grad.medrec.service;

import com.grad.medrec.config.BusinessException;
import com.grad.medrec.dto.AuthDto;
import com.grad.medrec.entity.UserAccount;
import com.grad.medrec.enumtype.UserStatus;
import com.grad.medrec.repository.UserAccountRepository;
import com.grad.medrec.security.AuthUserPrincipal;
import com.grad.medrec.security.JwtService;
import com.grad.medrec.security.SecurityUtils;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class AuthService {

    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;
    private final UserAccountRepository userAccountRepository;

    public AuthService(AuthenticationManager authenticationManager, JwtService jwtService, UserAccountRepository userAccountRepository) {
        this.authenticationManager = authenticationManager;
        this.jwtService = jwtService;
        this.userAccountRepository = userAccountRepository;
    }

    public AuthDto.LoginResponse login(AuthDto.LoginRequest request) {
        try {
            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(request.username(), request.password())
            );
            AuthUserPrincipal principal = (AuthUserPrincipal) authentication.getPrincipal();
            UserAccount user = userAccountRepository.findById(principal.getUserId())
                    .orElseThrow(() -> new BusinessException("user not found"));
            if (user.getStatus() != UserStatus.ACTIVE) {
                throw new BusinessException("account is disabled");
            }
            user.setLastLoginAt(LocalDateTime.now());
            userAccountRepository.save(user);

            String token = jwtService.generateToken(user.getId(), user.getUsername(), user.getRole().name());
            return new AuthDto.LoginResponse(token, toUserInfo(user));
        } catch (BadCredentialsException exception) {
            throw new BusinessException("invalid username or password");
        }
    }

    public AuthDto.UserInfo me() {
        Long userId = SecurityUtils.currentUserId();
        if (userId == null) {
            throw new BusinessException("not logged in");
        }
        UserAccount user = userAccountRepository.findById(userId)
                .orElseThrow(() -> new BusinessException("user not found"));
        return toUserInfo(user);
    }

    private AuthDto.UserInfo toUserInfo(UserAccount user) {
        return new AuthDto.UserInfo(user.getId(), user.getUsername(), user.getRole().name().toLowerCase(), user.getStatus().name());
    }
}
