import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:frontend/const/secure_storage.dart';
import 'package:frontend/screen/main_screen.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'package:http/http.dart' as http;

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  LoginScreenState createState() => LoginScreenState();
}

class LoginScreenState extends State<LoginScreen> {
  final SecureStorage secureStorage = SecureStorage();

  void loginWithKakao() async {
    try {
      try {
        // 카카오톡을 통한 로그인 시도
        await UserApi.instance.loginWithKakaoTalk();
      } catch (error) {
        // 카카오톡 설치되어 있지 않거나, 로그인 실패 시
        print("Fallback to Kakao Account Login: $error");
        await UserApi.instance.loginWithKakaoAccount();
      }

      await secureStorage.setLoginStatus("isLoggedIn", "true");

      /*
      --------------------사용자 정보 받아와서 저장하는 로직 추가
       */

      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (context) => const MainScreen()),
      );
    } catch (error) {
      print(error.toString());
    }
  }

  // 서버에 토큰을 전송하는 함수
  Future<void> sendTokenToServer(String accessToken) async {
    try {
      final response = await http.post(
        Uri.parse('https://yourserver.com/api/login'),
        headers: <String, String>{
          'Content-Type': 'application/json; charset=UTF-8',
        },
        body: jsonEncode(<String, String>{
          'token': accessToken,
        }),
      );

      if (response.statusCode == 200) {
        // 서버로부터의 응답 처리
        print('Token successfully sent to the server');
      } else {
        // 서버 에러 처리
        print('Failed to send token to the server');
      }
    } catch (e) {
      print('Error sending token to the server: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ElevatedButton(
          child: const Text('Login with Kakao'),
          onPressed: () => loginWithKakao(),
        ),
      ),
    );
  }
}
