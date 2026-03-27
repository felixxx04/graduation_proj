package com.grad.medrec.service;

import com.grad.medrec.dto.PrivacyDto;
import com.grad.medrec.dto.RecommendationDto;
import com.grad.medrec.entity.*;
import com.grad.medrec.enumtype.NoiseMechanism;
import com.grad.medrec.enumtype.PrivacyEventType;
import com.grad.medrec.repository.DrugRepository;
import com.grad.medrec.repository.RecommendationRepository;
import com.grad.medrec.repository.UserAccountRepository;
import com.grad.medrec.security.SecurityUtils;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.regex.Pattern;

@Service
public class RecommendationService {

    private static final Pattern SPLIT_PATTERN = Pattern.compile("[,，;；、|\\n]");

    private final DrugRepository drugRepository;
    private final RecommendationRepository recommendationRepository;
    private final UserAccountRepository userAccountRepository;
    private final PatientService patientService;
    private final PrivacyService privacyService;

    public RecommendationService(DrugRepository drugRepository,
                                 RecommendationRepository recommendationRepository,
                                 UserAccountRepository userAccountRepository,
                                 PatientService patientService,
                                 PrivacyService privacyService) {
        this.drugRepository = drugRepository;
        this.recommendationRepository = recommendationRepository;
        this.userAccountRepository = userAccountRepository;
        this.patientService = patientService;
        this.privacyService = privacyService;
    }

    @Transactional
    public RecommendationDto.GenerateResponse generate(RecommendationDto.GenerateRequest request) {
        Patient patient = request.patientId() == null ? null : patientService.findEntity(request.patientId());

        Profile profile = profileFrom(request, patient);
        List<Drug> drugs = drugRepository.findAll();
        if (drugs.isEmpty()) {
            throw new IllegalStateException("drug knowledge is empty");
        }

        int topK = request.topK() == null ? 4 : Math.max(1, Math.min(request.topK(), 8));
        PrivacyConfig config = privacyService.getCurrentConfig();

        List<RecommendationDto.Item> base = scoreDrugs(profile, drugs, false, config, topK);
        List<RecommendationDto.Item> dp = scoreDrugs(profile, drugs, true, config, topK);

        boolean dpEnabled = Boolean.TRUE.equals(request.dpEnabled());
        List<RecommendationDto.Item> selected = dpEnabled ? dp : base;

        double epsilonUsed = 0d;
        if (dpEnabled) {
            PrivacyDto.BudgetResponse budget = privacyService.currentBudget();
            if (budget.remaining() > 0) {
                epsilonUsed = Math.min(config.getEpsilon(), budget.remaining());
                privacyService.addEvent(
                        PrivacyEventType.RECOMMENDATION_INFERENCE,
                        epsilonUsed,
                        config.getNoiseMechanism() == NoiseMechanism.GAUSSIAN ? config.getDeltaValue() : null,
                        "mechanism=" + config.getNoiseMechanism() + ", stage=" + config.getApplicationStage() + ", topK=" + topK
                );
            }
        }

        Recommendation recommendation = new Recommendation();
        recommendation.setPatient(patient);
        recommendation.setAge(profile.age());
        recommendation.setGender(profile.gender());
        recommendation.setDiseases(String.join(",", profile.diseases()));
        recommendation.setSymptoms(profile.symptoms());
        recommendation.setAllergies(String.join(",", profile.allergies()));
        recommendation.setCurrentMedications(String.join(",", profile.currentMedications()));
        recommendation.setDpEnabled(dpEnabled);
        recommendation.setEpsilonUsed(epsilonUsed);
        recommendation.setNoiseMechanism(config.getNoiseMechanism());
        recommendation.setApplicationStage(config.getApplicationStage());

        Long userId = SecurityUtils.currentUserId();
        if (userId != null) {
            recommendation.setCreatedBy(userAccountRepository.findById(userId).orElse(null));
        }

        List<RecommendationItem> itemEntities = new ArrayList<>();
        for (int i = 0; i < selected.size(); i++) {
            RecommendationDto.Item selectedItem = selected.get(i);
            RecommendationItem item = new RecommendationItem();
            item.setRecommendation(recommendation);
            item.setDrug(drugs.stream().filter(d -> Objects.equals(d.getId(), selectedItem.drugId())).findFirst().orElseThrow());
            item.setRankIndex(i + 1);
            item.setScore(selectedItem.score());
            item.setConfidence(selectedItem.confidence());
            item.setDpNoise(selectedItem.dpNoise());
            item.setReason(selectedItem.reason());
            item.setInteractions(String.join("|", selectedItem.interactions()));
            item.setSideEffects(String.join("|", selectedItem.sideEffects()));
            item.setWarnings(String.join("|", selectedItem.explanation().warnings()));
            itemEntities.add(item);
        }
        recommendation.setItems(itemEntities);

        Recommendation saved = recommendationRepository.save(recommendation);
        return new RecommendationDto.GenerateResponse(saved.getId(), selected, base, dp, dpEnabled);
    }

    @Transactional
    public List<RecommendationDto.HistoryItem> history(int limit) {
        int max = Math.max(1, Math.min(limit, 50));
        return recommendationRepository.findAll().stream()
                .sorted(Comparator.comparing(Recommendation::getCreatedAt).reversed())
                .limit(max)
                .map(rec -> {
                    String patientName = rec.getPatient() == null ? null : rec.getPatient().getName();
                    Long patientId = rec.getPatient() == null ? null : rec.getPatient().getId();
                    List<RecommendationDto.Item> items = rec.getItems().stream()
                            .sorted(Comparator.comparing(RecommendationItem::getRankIndex))
                            .map(this::toItem)
                            .toList();
                    return new RecommendationDto.HistoryItem(
                            rec.getId(),
                            patientId,
                            patientName,
                            Boolean.TRUE.equals(rec.getDpEnabled()),
                            rec.getEpsilonUsed(),
                            rec.getCreatedAt(),
                            items
                    );
                })
                .toList();
    }

    private RecommendationDto.Item toItem(RecommendationItem item) {
        List<String> interactions = splitByPipe(item.getInteractions());
        List<String> sideEffects = splitByPipe(item.getSideEffects());
        List<String> warnings = splitByPipe(item.getWarnings());
        return new RecommendationDto.Item(
                item.getDrug().getId(),
                item.getDrug().getName(),
                item.getDrug().getCategory(),
                item.getDrug().getTypicalDosage(),
                item.getDrug().getTypicalFrequency(),
                item.getConfidence(),
                item.getScore(),
                item.getDpNoise(),
                item.getReason(),
                interactions,
                sideEffects,
                new RecommendationDto.Explanation(List.of(), warnings)
        );
    }

    private List<String> splitByPipe(String source) {
        if (source == null || source.isBlank()) {
            return List.of();
        }
        return Arrays.stream(source.split("\\|"))
                .map(String::trim)
                .filter(s -> !s.isBlank())
                .toList();
    }

    private List<RecommendationDto.Item> scoreDrugs(Profile profile, List<Drug> drugs, boolean applyDp, PrivacyConfig config, int topK) {
        List<ScoredDrug> raw = drugs.stream().map(drug -> scoreDrug(profile, drug, applyDp, config)).toList();
        List<Double> rawScores = raw.stream().map(ScoredDrug::rawScore).toList();

        return raw.stream()
                .map(scored -> {
                    double confidence = softConfidence(rawScores, scored.rawScore());
                    String reason = buildReason(scored.features());
                    return new RecommendationDto.Item(
                            scored.drug().getId(),
                            scored.drug().getName(),
                            scored.drug().getCategory(),
                            scored.drug().getTypicalDosage(),
                            scored.drug().getTypicalFrequency(),
                            confidence,
                            round(scored.finalScore()),
                            applyDp ? round(scored.dpNoise()) : null,
                            reason,
                            scored.interactions(),
                            scored.drug().getCommonSideEffects(),
                            new RecommendationDto.Explanation(scored.features(), scored.warnings())
                    );
                })
                .sorted(Comparator.comparing(RecommendationDto.Item::score).reversed())
                .limit(topK)
                .toList();
    }

    private ScoredDrug scoreDrug(Profile profile, Drug drug, boolean applyDp, PrivacyConfig config) {
        List<RecommendationDto.ExplanationFeature> features = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        List<String> interactions = new ArrayList<>();

        int indicationMatches = matchCount(profile.diseases(), drug.getIndications());
        double indicationWeight = 3.2;
        double indicationContribution = indicationMatches * indicationWeight;
        features.add(new RecommendationDto.ExplanationFeature("indication_match", indicationWeight, indicationContribution, indicationMatches > 0 ? "matched=" + indicationMatches : "none"));

        double comorbidityWeight = 1.6;
        boolean comorbidityHit = includesAny(profile.diseases(), List.of("coronary", "atherosclerosis", "heart"))
                && includesAny(drug.getIndications(), List.of("coronary", "atherosclerosis", "heart"));
        double comorbidityContribution = comorbidityHit ? comorbidityWeight : 0;
        features.add(new RecommendationDto.ExplanationFeature("comorbidity", comorbidityWeight, comorbidityContribution, comorbidityHit ? "hit" : "none"));

        double allergyPenaltyWeight = -6.5;
        boolean allergyHit = includesAny(profile.allergies(), List.of(drug.getName()))
                || (includesAny(profile.allergies(), List.of("aspirin")) && drug.getName().toLowerCase().contains("aspirin"));
        double allergyPenalty = allergyHit ? allergyPenaltyWeight : 0;
        if (allergyHit) {
            warnings.add("possible allergy risk for " + drug.getName());
        }
        features.add(new RecommendationDto.ExplanationFeature("allergy_risk", allergyPenaltyWeight, allergyPenalty, allergyHit ? "hit" : "none"));

        double contraindicationPenaltyWeight = -4.0;
        boolean contraindicationHit = includesAny(profile.diseases(), drug.getContraindications());
        double contraindicationPenalty = contraindicationHit ? contraindicationPenaltyWeight : 0;
        if (contraindicationHit) {
            warnings.add("possible contraindication with patient conditions");
        }
        features.add(new RecommendationDto.ExplanationFeature("contraindication", contraindicationPenaltyWeight, contraindicationPenalty, contraindicationHit ? "hit" : "none"));

        double interactionPenaltyWeight = -2.4;
        boolean interactionHit = includesAny(profile.currentMedications(), drug.getInteractionsWith());
        double interactionPenalty = interactionHit ? interactionPenaltyWeight : 0;
        if (interactionHit) {
            warnings.add("interaction risk with current medication");
            interactions.add("check interaction with " + String.join(",", drug.getInteractionsWith()));
        } else if (!drug.getInteractionsWith().isEmpty()) {
            interactions.add("general caution: " + String.join(",", drug.getInteractionsWith()));
        }
        features.add(new RecommendationDto.ExplanationFeature("interaction_risk", interactionPenaltyWeight, interactionPenalty, interactionHit ? "hit" : "none"));

        double ageWeight = 0.6;
        double ageContribution = profile.age() != null && profile.age() >= 60 ? ageWeight : 0;
        features.add(new RecommendationDto.ExplanationFeature("age_factor", ageWeight, ageContribution, profile.age() == null ? "unknown" : String.valueOf(profile.age())));

        double score = features.stream().mapToDouble(RecommendationDto.ExplanationFeature::contribution).sum();

        double finalScore = score;
        double noise = 0d;
        if (applyDp) {
            DpResult result = applyNoise(score, config);
            finalScore = result.noisy();
            noise = result.noise();
        }

        return new ScoredDrug(drug, score, finalScore, noise, features, warnings, interactions);
    }

    private String buildReason(List<RecommendationDto.ExplanationFeature> features) {
        String core = features.stream()
                .filter(f -> Math.abs(f.contribution()) > 0.00001)
                .sorted((a, b) -> Double.compare(Math.abs(b.contribution()), Math.abs(a.contribution())))
                .limit(3)
                .map(f -> f.name() + (f.note() == null ? "" : "(" + f.note() + ")"))
                .reduce((a, b) -> a + ", " + b)
                .orElse("comprehensive patient-drug match");
        return "top signals: " + core;
    }

    private Profile profileFrom(RecommendationDto.GenerateRequest request, Patient patient) {
        Integer age = parseIntOrNull(firstNonBlank(request.age(), patient == null ? null : String.valueOf(patient.getAge())));
        String gender = firstNonBlank(request.gender(), patient == null ? null : patient.getGender().name());

        List<String> diseases = toList(firstNonBlank(request.diseases(), patient == null ? null : String.join(",", patient.getChronicDiseases())));
        List<String> allergies = toList(firstNonBlank(request.allergies(), patient == null ? null : String.join(",", patient.getAllergies())));
        List<String> currentMedications = toList(firstNonBlank(request.currentMedications(), patient == null ? null : String.join(",", patient.getCurrentMedications())));
        String symptoms = firstNonBlank(request.symptoms(), patient == null ? null : patient.getMedicalHistory());

        return new Profile(age, gender, diseases, symptoms == null ? "" : symptoms, allergies, currentMedications);
    }

    private String firstNonBlank(String first, String second) {
        if (first != null && !first.isBlank()) {
            return first;
        }
        return second;
    }

    private Integer parseIntOrNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Integer.parseInt(value.trim());
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private List<String> toList(String value) {
        if (value == null || value.isBlank()) {
            return List.of();
        }
        return Arrays.stream(SPLIT_PATTERN.split(value))
                .map(String::trim)
                .filter(s -> !s.isBlank())
                .toList();
    }

    private boolean includesAny(List<String> haystack, List<String> needles) {
        List<String> hs = haystack.stream().map(v -> v.toLowerCase(Locale.ROOT)).toList();
        for (String needle : needles) {
            String n = needle.toLowerCase(Locale.ROOT);
            for (String h : hs) {
                if (h.contains(n) || n.contains(h)) {
                    return true;
                }
            }
        }
        return false;
    }

    private int matchCount(List<String> haystack, List<String> needles) {
        int count = 0;
        for (String needle : needles) {
            if (includesAny(haystack, List.of(needle))) {
                count++;
            }
        }
        return count;
    }

    private double softConfidence(List<Double> scores, double score) {
        double max = scores.stream().mapToDouble(v -> v).max().orElse(0);
        List<Double> shifted = scores.stream().map(s -> Math.exp((s - max) / 6)).toList();
        double sum = shifted.stream().mapToDouble(v -> v).sum();
        if (sum <= 0) {
            return 70;
        }
        double p = Math.exp((score - max) / 6) / sum;
        double conf = 70 + 28 * Math.min(1, Math.max(0, p * 3.2));
        return round(conf);
    }

    private DpResult applyNoise(double score, PrivacyConfig config) {
        if (config.getEpsilon() == null || config.getEpsilon() <= 0) {
            return new DpResult(score, 0);
        }
        double epsilon = Math.max(1e-6, config.getEpsilon());
        double sensitivity = Math.max(1e-6, config.getSensitivity());

        if (config.getNoiseMechanism() == NoiseMechanism.GAUSSIAN) {
            double delta = Math.min(0.5, Math.max(1e-12, config.getDeltaValue()));
            double sigma = (sensitivity * Math.sqrt(2 * Math.log(1.25 / delta))) / epsilon;
            double noise = new Random().nextGaussian() * sigma;
            return new DpResult(score + noise, noise);
        }

        double scale = sensitivity / epsilon;
        double noise = sampleLaplace(scale);
        if (config.getNoiseMechanism() == NoiseMechanism.GEOMETRIC) {
            noise = Math.round(noise);
        }
        return new DpResult(score + noise, noise);
    }

    private double sampleLaplace(double scale) {
        double u = Math.random() - 0.5;
        double sign = u < 0 ? -1 : 1;
        return -scale * sign * Math.log(1 - 2 * Math.abs(u));
    }

    private double round(double v) {
        return Math.round(v * 1000d) / 1000d;
    }

    private record DpResult(double noisy, double noise) {
    }

    private record Profile(Integer age, String gender, List<String> diseases, String symptoms,
                           List<String> allergies, List<String> currentMedications) {
    }

    private record ScoredDrug(Drug drug, double rawScore, double finalScore, double dpNoise,
                              List<RecommendationDto.ExplanationFeature> features,
                              List<String> warnings,
                              List<String> interactions) {
    }
}
