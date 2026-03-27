package com.grad.medrec.service;

import com.grad.medrec.config.BusinessException;
import com.grad.medrec.dto.PatientDto;
import com.grad.medrec.entity.Patient;
import com.grad.medrec.entity.UserAccount;
import com.grad.medrec.repository.PatientRepository;
import com.grad.medrec.repository.UserAccountRepository;
import com.grad.medrec.security.SecurityUtils;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PatientService {

    private final PatientRepository patientRepository;
    private final UserAccountRepository userAccountRepository;

    public PatientService(PatientRepository patientRepository, UserAccountRepository userAccountRepository) {
        this.patientRepository = patientRepository;
        this.userAccountRepository = userAccountRepository;
    }

    public List<PatientDto.Item> list() {
        return patientRepository.findAll().stream().map(this::toDto).toList();
    }

    public PatientDto.Item create(PatientDto.UpsertRequest request) {
        Patient patient = new Patient();
        apply(patient, request);
        Long userId = SecurityUtils.currentUserId();
        if (userId != null) {
            UserAccount user = userAccountRepository.findById(userId).orElse(null);
            patient.setCreatedBy(user);
        }
        return toDto(patientRepository.save(patient));
    }

    public PatientDto.Item update(Long id, PatientDto.UpsertRequest request) {
        Patient patient = patientRepository.findById(id)
                .orElseThrow(() -> new BusinessException("patient not found"));
        apply(patient, request);
        return toDto(patientRepository.save(patient));
    }

    public void delete(Long id) {
        if (!patientRepository.existsById(id)) {
            throw new BusinessException("patient not found");
        }
        patientRepository.deleteById(id);
    }

    public Patient findEntity(Long id) {
        return patientRepository.findById(id).orElse(null);
    }

    private void apply(Patient patient, PatientDto.UpsertRequest request) {
        patient.setName(request.name());
        patient.setAge(request.age());
        patient.setGender(request.gender());
        patient.setHeight(request.height());
        patient.setWeight(request.weight());
        patient.setMedicalHistory(request.medicalHistory());
        patient.setAllergies(request.allergies() == null ? List.of() : request.allergies().stream().filter(s -> !s.isBlank()).toList());
        patient.setChronicDiseases(request.chronicDiseases() == null ? List.of() : request.chronicDiseases().stream().filter(s -> !s.isBlank()).toList());
        patient.setCurrentMedications(request.currentMedications() == null ? List.of() : request.currentMedications().stream().filter(s -> !s.isBlank()).toList());
    }

    private PatientDto.Item toDto(Patient patient) {
        return new PatientDto.Item(
                patient.getId(),
                patient.getName(),
                patient.getAge(),
                patient.getGender(),
                patient.getHeight(),
                patient.getWeight(),
                patient.getAllergies(),
                patient.getChronicDiseases(),
                patient.getCurrentMedications(),
                patient.getMedicalHistory(),
                patient.getCreatedAt()
        );
    }
}
