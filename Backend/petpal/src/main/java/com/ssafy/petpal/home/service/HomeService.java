package com.ssafy.petpal.home.service;

import com.ssafy.petpal.home.dto.HomeRequestDTO;
import com.ssafy.petpal.home.entity.Home;
import com.ssafy.petpal.home.repository.HomeRepository;
import com.ssafy.petpal.user.entity.User;
import com.ssafy.petpal.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class HomeService {

    private final HomeRepository homeRepository;
    private final UserRepository userRepository;

    public long createHome(HomeRequestDTO homeRequestDTO) {
        log.info("23");
//        User user = userRepository.findByUserId(homeRequestDTO.getUserId())
//                .orElseThrow(IllegalArgumentException::new);

        Home home = Home.builder()
//                .homeNickname(homeRequestDTO.getHomeNickname())
                .kakaoId(homeRequestDTO.getUserId())
                .build();
//        log.info("31 " + home.getHomeNickname());
        Home returnHome = homeRepository.save(home);
        log.info("33");
        return returnHome.getId();
    }

    public List<Home> fetchAllByUserId(Long userId) {
        return homeRepository.findByKakaoId(userId);
    }
}
