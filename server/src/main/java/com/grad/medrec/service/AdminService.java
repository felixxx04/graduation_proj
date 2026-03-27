package com.grad.medrec.service;

import com.grad.medrec.config.BusinessException;
import com.grad.medrec.dto.AdminDto;
import com.grad.medrec.entity.*;
import com.grad.medrec.enumtype.PrivacyEventType;
import com.grad.medrec.enumtype.TrainingRunStatus;
import com.grad.medrec.repository.*;
import com.grad.medrec.security.SecurityUtils;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;

@Service
public class AdminService {

    private final UserAccountRepository userAccountRepository;
    private final TrainingRunRepository trainingRunRepository;
    private final PrivacyService privacyService;
    private final RecommendationRepository recommendationRepository;
    private final PatientRepository patientRepository;
    private final PrivacyEventRepository privacyEventRepository;

    public AdminService(UserAccountRepository userAccountRepository,
                        TrainingRunRepository trainingRunRepository,
                        PrivacyService privacyService,
                        RecommendationRepository recommendationRepository,
                        PatientRepository patientRepository,
                        PrivacyEventRepository privacyEventRepository) {
        this.userAccountRepository = userAccountRepository;
        this.trainingRunRepository = trainingRunRepository;
        this.privacyService = privacyService;
        this.recommendationRepository = recommendationRepository;
        this.patientRepository = patientRepository;
        this.privacyEventRepository = privacyEventRepository;
    }

    public List<AdminDto.UserItem> listUsers() {
        return userAccountRepository.findAll().stream()
                .sorted(Comparator.comparing(UserAccount::getId))
                .map(u -> new AdminDto.UserItem(
                        u.getId(),
                        u.getUsername(),
                        u.getRole().name().toLowerCase(),
                        u.getStatus(),
                        u.getLastLoginAt()
                ))
                .toList();
    }

    public AdminDto.UserItem updateUserStatus(Long id, AdminDto.UpdateUserStatusRequest request) {
        UserAccount user = userAccountRepository.findById(id)
                .orElseThrow(() -> new BusinessException("user not found"));
        if (request.status() == null) {
            throw new BusinessException("status is required");
        }
        user.setStatus(request.status());
        UserAccount saved = userAccountRepository.save(user);
        return new AdminDto.UserItem(
                saved.getId(),
                saved.getUsername(),
                saved.getRole().name().toLowerCase(),
                saved.getStatus(),
                saved.getLastLoginAt()
        );
    }

    @Transactional
    public AdminDto.TrainingRunItem startTraining(AdminDto.StartTrainingRequest request) {
        int epochs = request.epochs() == null ? 10 : Math.max(1, Math.min(request.epochs(), 50));
        PrivacyConfig config = privacyService.getCurrentConfig();

        TrainingRun run = new TrainingRun();
        run.setStatus(TrainingRunStatus.RUNNING);
        run.setTotalEpochs(epochs);
        run.setEpsilonPerEpoch(config.getEpsilon() / epochs);
        run.setStartedAt(LocalDateTime.now());

        Long userId = SecurityUtils.currentUserId();
        if (userId != null) {
            run.setCreatedBy(userAccountRepository.findById(userId).orElse(null));
        }

        for (int epoch = 1; epoch <= epochs; epoch++) {
            double t = (double) epoch / epochs;
            double loss = round(1.8 * Math.exp(-3 * t) + 0.15 + (Math.random() - 0.5) * 0.04);
            double accuracy = round(60 + 28 * (1 - Math.exp(-4 * t)) + (Math.random() - 0.5) * 1.5);

            double epsilonPerEpoch = config.getEpsilon() / epochs;
            double remaining = privacyService.currentBudget().remaining();
            double spent = Math.min(epsilonPerEpoch, Math.max(remaining, 0d));

            privacyService.addEvent(
                    PrivacyEventType.TRAINING_EPOCH,
                    spent,
                    config.getNoiseMechanism().name().equals("GAUSSIAN") ? config.getDeltaValue() : null,
                    "epoch=" + epoch + ", loss=" + loss + ", acc=" + accuracy
            );

            TrainingEpoch trainingEpoch = new TrainingEpoch();
            trainingEpoch.setTrainingRun(run);
            trainingEpoch.setEpochIndex(epoch);
            trainingEpoch.setLoss(loss);
            trainingEpoch.setAccuracy(accuracy);
            trainingEpoch.setEpsilonSpent(spent);
            run.getEpochs().add(trainingEpoch);
        }

        run.setStatus(TrainingRunStatus.COMPLETED);
        run.setFinishedAt(LocalDateTime.now());

        TrainingRun saved = trainingRunRepository.save(run);
        return toRunItem(saved);
    }

    public List<AdminDto.TrainingRunItem> trainingHistory(int limit) {
        int max = Math.max(1, Math.min(limit, 30));
        return trainingRunRepository.findAll().stream()
                .sorted(Comparator.comparing(TrainingRun::getStartedAt).reversed())
                .limit(max)
                .map(this::toRunItem)
                .toList();
    }

    public AdminDto.DashboardResponse dashboard() {
        long patientCount = patientRepository.count();
        long userCount = userAccountRepository.count();
        long recommendationCount = recommendationRepository.count();
        long eventCount = privacyEventRepository.count();

        double spent = privacyEventRepository.sumEpsilonSpent();
        double remaining = Math.max(0d, privacyService.getCurrentConfig().getPrivacyBudget() - spent);

        return new AdminDto.DashboardResponse(
                patientCount,
                userCount,
                recommendationCount,
                eventCount,
                round(spent),
                round(remaining)
        );
    }

    private AdminDto.TrainingRunItem toRunItem(TrainingRun run) {
        List<AdminDto.TrainingEpochItem> epochs = run.getEpochs().stream()
                .sorted(Comparator.comparing(TrainingEpoch::getEpochIndex))
                .map(e -> new AdminDto.TrainingEpochItem(
                        e.getEpochIndex(),
                        e.getLoss(),
                        e.getAccuracy(),
                        e.getEpsilonSpent(),
                        e.getCreatedAt()
                ))
                .toList();
        return new AdminDto.TrainingRunItem(
                run.getId(),
                run.getStatus(),
                run.getTotalEpochs(),
                run.getEpsilonPerEpoch(),
                run.getStartedAt(),
                run.getFinishedAt(),
                epochs
        );
    }

    private double round(double v) {
        return Math.round(v * 1000d) / 1000d;
    }
}
