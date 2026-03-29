package com.medical.service;

import com.medical.entity.User;
import com.medical.repository.UserRepository;
import com.medical.security.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class AuthService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    
    public Map<String, Object> login(String username, String password) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new RuntimeException("用户不存在"));
        
        if (!user.getEnabled()) {
            throw new RuntimeException("用户已禁用");
        }
        
        if (!passwordEncoder.matches(password, user.getPasswordHash())) {
            throw new RuntimeException("密码错误");
        }
        
        String token = jwtUtil.generateToken(username, user.getRole());
        
        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("user", Map.of(
            "id", user.getId(),
            "username", user.getUsername(),
            "role", user.getRole()
        ));
        return result;
    }
    
    public User getCurrentUser(String username) {
        return userRepository.findByUsername(username).orElse(null);
    }
}
