package com.medical.service;

import com.medical.config.ModelServiceConfig;
import com.medical.entity.User;
import com.medical.repository.DrugRepository;
import com.medical.repository.PrivacyRepository;
import com.medical.repository.RecommendationRepository;
import com.medical.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.Mockito.lenient;

@ExtendWith(MockitoExtension.class)
class RecommendationServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock(lenient = true)
    private DrugService drugService;

    @Mock
    private RecommendationRepository recommendationRepository;

    @Mock
    private PrivacyRepository privacyRepository;

    @Mock(lenient = true)
    private ModelServiceConfig modelServiceConfig;

    @InjectMocks
    private RecommendationService service;

    @BeforeEach
    void setUp() {
        lenient().when(modelServiceConfig.getUrl()).thenReturn("http://localhost:8001");
        lenient().when(modelServiceConfig.getInitDelayMs()).thenReturn(100);
    }

    @Test
    @DisplayName("getCurrentUserId should return correct ID for authenticated user")
    void getCurrentUserId_authenticatedUser_returnsId() {
        // Arrange
        User user = new User();
        user.setId(42L);
        user.setUsername("testuser");

        when(userRepository.findByUsername("testuser")).thenReturn(Optional.of(user));

        Authentication auth = mock(Authentication.class);
        when(auth.isAuthenticated()).thenReturn(true);
        when(auth.getName()).thenReturn("testuser");

        SecurityContext context = mock(SecurityContext.class);
        when(context.getAuthentication()).thenReturn(auth);

        try (var mocked = mockStatic(SecurityContextHolder.class)) {
            mocked.when(SecurityContextHolder::getContext).thenReturn(context);

            // Act
            Long result = invokeGetCurrentUserId();

            // Assert
            assertThat(result).isEqualTo(42L);
        }
    }

    @Test
    @DisplayName("getCurrentUserId should throw for non-existent user")
    void getCurrentUserId_nonExistentUser_throws() {
        when(userRepository.findByUsername("ghost")).thenReturn(Optional.empty());

        Authentication auth = mock(Authentication.class);
        when(auth.isAuthenticated()).thenReturn(true);
        when(auth.getName()).thenReturn("ghost");

        SecurityContext context = mock(SecurityContext.class);
        when(context.getAuthentication()).thenReturn(auth);

        try (var mocked = mockStatic(SecurityContextHolder.class)) {
            mocked.when(SecurityContextHolder::getContext).thenReturn(context);

            assertThatThrownBy(this::invokeGetCurrentUserId)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("ghost");
        }
    }

    @Test
    @DisplayName("getCurrentUserId should return null for unauthenticated user")
    void getCurrentUserId_unauthenticated_returnsNull() {
        Authentication auth = mock(Authentication.class);
        when(auth.isAuthenticated()).thenReturn(false);

        SecurityContext context = mock(SecurityContext.class);
        when(context.getAuthentication()).thenReturn(auth);

        try (var mocked = mockStatic(SecurityContextHolder.class)) {
            mocked.when(SecurityContextHolder::getContext).thenReturn(context);

            Long result = invokeGetCurrentUserId();
            assertThat(result).isNull();
        }
    }

    /**
     * Helper method to access private getCurrentUserId method for testing
     */
    private Long invokeGetCurrentUserId() {
        try {
            var method = RecommendationService.class.getDeclaredMethod("getCurrentUserId");
            method.setAccessible(true);
            return (Long) method.invoke(service);
        } catch (Exception e) {
            if (e.getCause() instanceof IllegalStateException) {
                throw (IllegalStateException) e.getCause();
            }
            throw new RuntimeException(e);
        }
    }
}
