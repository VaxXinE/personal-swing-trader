import 'dart:convert';
import 'package:http/http.dart' as http;

class SwingApi {
  SwingApi({required this.baseUrl, this.token = ''});
  String baseUrl;
  String token;

  Uri _uri(String path) => Uri.parse('${baseUrl.replaceAll(RegExp(r"/+$"), '')}/v1$path');

  Future<Map<String, dynamic>> call(String path,
      {String method = 'GET', Map<String, dynamic>? body}) async {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token.isNotEmpty) headers['Authorization'] = 'Bearer $token';
    http.Response response;
    try {
      final url = _uri(path);
      if (method == 'POST') {
        response = await http.post(url, headers: headers,
            body: jsonEncode(body ?? <String, dynamic>{})).timeout(const Duration(seconds: 90));
      } else if (method == 'DELETE') {
        response = await http.delete(url, headers: headers).timeout(const Duration(seconds: 15));
      } else {
        response = await http.get(url, headers: headers).timeout(const Duration(seconds: 90));
      }
    } catch (e) {
      throw Exception('Cannot reach private backend. Check URL/VPN: $e');
    }
    final decoded = jsonDecode(response.body);
    if (response.statusCode >= 400) {
      throw Exception(decoded is Map ? (decoded['detail'] ?? response.statusCode).toString()
          : 'Server error ${response.statusCode}');
    }
    return Map<String, dynamic>.from(decoded as Map);
  }

  Future<List<Map<String, dynamic>>> opportunities() async {
    final body = await call('/opportunities');
    return (body['items'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }
  Future<List<Map<String, dynamic>>> watches() async {
    final body = await call('/watchlist');
    return (body['items'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }
  Future<List<Map<String, dynamic>>> journal() async {
    final body = await call('/journal/trades');
    return (body['items'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }
  Future<void> scan() async {
    await call('/screeners/runs', method: 'POST', body: {
      'name': 'All Opportunities', 'markets': ['US', 'IDX', 'CRYPTO'],
      'strategy': 'BOTH', 'rules': {'op': 'AND', 'children': <dynamic>[]}
    });
  }
}
