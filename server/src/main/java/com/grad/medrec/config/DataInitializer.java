package com.grad.medrec.config;

import com.grad.medrec.entity.Drug;
import com.grad.medrec.entity.Patient;
import com.grad.medrec.entity.PrivacyConfig;
import com.grad.medrec.entity.UserAccount;
import com.grad.medrec.enumtype.*;
import com.grad.medrec.repository.DrugRepository;
import com.grad.medrec.repository.PatientRepository;
import com.grad.medrec.repository.PrivacyConfigRepository;
import com.grad.medrec.repository.UserAccountRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.List;

@Configuration
public class DataInitializer {

    @Bean
    CommandLineRunner seedData(UserAccountRepository userRepository,
                               PatientRepository patientRepository,
                               PrivacyConfigRepository privacyConfigRepository,
                               DrugRepository drugRepository,
                               PasswordEncoder passwordEncoder) {
        return args -> {
            if (userRepository.count() == 0) {
                UserAccount user = new UserAccount();
                user.setUsername("user");
                user.setPasswordHash(passwordEncoder.encode("123456"));
                user.setRole(UserRole.USER);
                user.setStatus(UserStatus.ACTIVE);

                UserAccount admin = new UserAccount();
                admin.setUsername("admin");
                admin.setPasswordHash(passwordEncoder.encode("123456"));
                admin.setRole(UserRole.ADMIN);
                admin.setStatus(UserStatus.ACTIVE);

                userRepository.saveAll(List.of(user, admin));
            }

            if (privacyConfigRepository.count() == 0) {
                PrivacyConfig config = new PrivacyConfig();
                config.setEpsilon(1.0);
                config.setDeltaValue(0.00001);
                config.setSensitivity(1.0);
                config.setNoiseMechanism(NoiseMechanism.LAPLACE);
                config.setApplicationStage(ApplicationStage.GRADIENT);
                config.setPrivacyBudget(10.0);
                privacyConfigRepository.save(config);
            }

            if (patientRepository.count() == 0) {
                UserAccount admin = userRepository.findByUsername("admin").orElse(null);

                Patient p1 = new Patient();
                p1.setName("Patient A");
                p1.setAge(45);
                p1.setGender(PatientGender.MALE);
                p1.setHeight(175d);
                p1.setWeight(70d);
                p1.setAllergies(List.of("penicillin", "aspirin"));
                p1.setChronicDiseases(List.of("hypertension", "type2 diabetes"));
                p1.setCurrentMedications(List.of("metformin", "amlodipine"));
                p1.setMedicalHistory("T2D for 5 years, hypertension for 3 years");
                p1.setCreatedBy(admin);

                Patient p2 = new Patient();
                p2.setName("Patient B");
                p2.setAge(62);
                p2.setGender(PatientGender.FEMALE);
                p2.setHeight(160d);
                p2.setWeight(58d);
                p2.setAllergies(List.of("sulfa"));
                p2.setChronicDiseases(List.of("coronary heart disease"));
                p2.setCurrentMedications(List.of("aspirin", "atorvastatin"));
                p2.setMedicalHistory("CHD history of 8 years");
                p2.setCreatedBy(admin);

                patientRepository.saveAll(List.of(p1, p2));
            }

            if (drugRepository.count() == 0) {
                drugRepository.saveAll(List.of(
                        drug("metformin_xr", "Metformin XR", "glucose_lowering", "500mg", "twice daily with meals",
                                List.of("type2 diabetes", "diabetes"),
                                List.of("severe renal impairment", "lactic acidosis"),
                                List.of("gastrointestinal discomfort", "fatigue"),
                                List.of("contrast agent", "alcohol")),
                        drug("amlodipine", "Amlodipine", "blood_pressure", "5mg", "once daily",
                                List.of("hypertension", "coronary heart disease"),
                                List.of("severe hypotension"),
                                List.of("edema", "headache"),
                                List.of("grapefruit")),
                        drug("atorvastatin", "Atorvastatin", "lipid_lowering", "20mg", "once nightly",
                                List.of("hyperlipidemia", "atherosclerosis", "coronary heart disease"),
                                List.of("active liver disease", "pregnancy"),
                                List.of("myalgia", "abnormal liver function"),
                                List.of("macrolide antibiotics", "grapefruit")),
                        drug("aspirin_ec", "Aspirin EC", "antiplatelet", "100mg", "once daily",
                                List.of("coronary heart disease", "atherosclerosis"),
                                List.of("active bleeding", "aspirin allergy"),
                                List.of("gastrointestinal bleeding risk", "stomach pain"),
                                List.of("anticoagulants", "NSAIDs")),
                        drug("losartan", "Losartan", "blood_pressure", "50mg", "once daily",
                                List.of("hypertension", "diabetic nephropathy"),
                                List.of("pregnancy", "bilateral renal artery stenosis"),
                                List.of("dizziness", "fatigue"),
                                List.of("potassium supplements", "potassium-sparing diuretics")),
                        drug("omeprazole", "Omeprazole", "digestive", "20mg", "once daily before breakfast",
                                List.of("ulcer", "gerd"),
                                List.of("ppi allergy"),
                                List.of("abdominal pain", "headache"),
                                List.of("clopidogrel"))
                ));
            }
        };
    }

    private Drug drug(String code,
                      String name,
                      String category,
                      String dosage,
                      String frequency,
                      List<String> indications,
                      List<String> contraindications,
                      List<String> sideEffects,
                      List<String> interactions) {
        Drug drug = new Drug();
        drug.setCode(code);
        drug.setName(name);
        drug.setCategory(category);
        drug.setTypicalDosage(dosage);
        drug.setTypicalFrequency(frequency);
        drug.setIndications(indications);
        drug.setContraindications(contraindications);
        drug.setCommonSideEffects(sideEffects);
        drug.setInteractionsWith(interactions);
        return drug;
    }
}
