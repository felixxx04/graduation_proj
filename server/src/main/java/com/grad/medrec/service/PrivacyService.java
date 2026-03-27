package com.grad.medrec.service;

import com.grad.medrec.config.BusinessException;
import com.grad.medrec.dto.PrivacyDto;
import com.grad.medrec.entity.PrivacyConfig;
import com.grad.medrec.entity.PrivacyEvent;
import com.grad.medrec.entity.UserAccount;
import com.grad.medrec.enumtype.PrivacyEventType;
import com.grad.medrec.repository.PrivacyConfigRepository;
import com.grad.medrec.repository.PrivacyEventRepository;
import com.grad.medrec.repository.UserAccountRepository;
import com.grad.medrec.security.SecurityUtils;
import org.springframework.stereotype.Service;

import java.util.Comparator;
import java.util.List;

@Service
public class PrivacyService {

    private final PrivacyConfigRepository privacyConfigRepository;
    private final PrivacyEventRepository privacyEventRepository;
    private final UserAccountRepository userAccountRepository;

    public PrivacyService(PrivacyConfigRepository privacyConfigRepository,
                          PrivacyEventRepository privacyEventRepository,
                          UserAccountRepository userAccountRepository) {
        this.privacyConfigRepository = privacyConfigRepository;
        this.privacyEventRepository = privacyEventRepository;
        this.userAccountRepository = userAccountRepository;
    }

    public PrivacyDto.ConfigWithBudget getConfigWithBudget() {
        PrivacyConfig config = getCurrentConfig();
        PrivacyDto.ConfigResponse cfg = toConfigResponse(config);
        PrivacyDto.BudgetResponse budget = budgetResponse(config.getPrivacyBudget(), privacyEventRepository.sumEpsilonSpent());
        List<PrivacyDto.EventItem> events = privacyEventRepository.findAll().stream()
                .sorted(Comparator.comparing(PrivacyEvent::getCreatedAt).reversed())
                .limit(30)
                .map(this::toEventItem)
                .toList();
        return new PrivacyDto.ConfigWithBudget(cfg, budget, events);
    }

    public PrivacyDto.ConfigResponse updateConfig(PrivacyDto.ConfigRequest request) {
        PrivacyConfig config = getCurrentConfig();
        config.setEpsilon(request.epsilon());
        config.setDeltaValue(request.delta());
        config.setSensitivity(request.sensitivity());
        config.setNoiseMechanism(request.noiseMechanism());
        config.setApplicationStage(request.applicationStage());
        config.setPrivacyBudget(request.privacyBudget());
        return toConfigResponse(privacyConfigRepository.save(config));
    }

    public List<PrivacyDto.EventItem> listEvents(int limit) {
        return privacyEventRepository.findAll().stream()
                .sorted(Comparator.comparing(PrivacyEvent::getCreatedAt).reversed())
                .limit(Math.max(1, Math.min(limit, 500)))
                .map(this::toEventItem)
                .toList();
    }

    public void clearEvents() {
        privacyEventRepository.deleteAll();
    }

    public PrivacyConfig getCurrentConfig() {
        return privacyConfigRepository.findAll().stream().findFirst()
                .orElseThrow(() -> new BusinessException("privacy config not initialized"));
    }

    public PrivacyDto.BudgetResponse currentBudget() {
        PrivacyConfig config = getCurrentConfig();
        return budgetResponse(config.getPrivacyBudget(), privacyEventRepository.sumEpsilonSpent());
    }

    public PrivacyEvent addEvent(PrivacyEventType type, double epsilonSpent, Double deltaSpent, String note) {
        PrivacyEvent event = new PrivacyEvent();
        event.setType(type);
        event.setEpsilonSpent(epsilonSpent);
        event.setDeltaSpent(deltaSpent);
        event.setNote(note);

        Long userId = SecurityUtils.currentUserId();
        if (userId != null) {
            UserAccount user = userAccountRepository.findById(userId).orElse(null);
            event.setCreatedBy(user);
        }

        return privacyEventRepository.save(event);
    }

    private PrivacyDto.ConfigResponse toConfigResponse(PrivacyConfig config) {
        return new PrivacyDto.ConfigResponse(
                config.getId(),
                config.getEpsilon(),
                config.getDeltaValue(),
                config.getSensitivity(),
                config.getNoiseMechanism(),
                config.getApplicationStage(),
                config.getPrivacyBudget()
        );
    }

    private PrivacyDto.EventItem toEventItem(PrivacyEvent event) {
        return new PrivacyDto.EventItem(
                event.getId(),
                event.getType(),
                event.getEpsilonSpent(),
                event.getDeltaSpent(),
                event.getNote(),
                event.getCreatedAt()
        );
    }

    private PrivacyDto.BudgetResponse budgetResponse(double total, double spent) {
        double remaining = Math.max(0d, total - spent);
        return new PrivacyDto.BudgetResponse(total, spent, remaining);
    }
}
