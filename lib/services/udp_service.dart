import 'dart:async';
import 'dart:io';

/// Handles all UDP communication with the TF-F6 LED controller.
///
/// Commands are queued and dispatched with a configurable inter-command delay.
/// Default is 120 ms, matching the Python app behaviour.
class UdpService {
  static const String controllerIp   = '192.168.1.252';
  static const int    controllerPort = 5959;
  static const Duration _testTimeout = Duration(seconds: 2);

  /// Gap between consecutive queued commands. Tune via UDP Timing settings.
  int commandDelayMs = 120;

  // Queue
  final _queue = <String>[];
  bool _processing = false;

  /// Bypass mode: log commands instead of sending.
  bool bypassMode = false;

  // ─── Public API ────────────────────────────────────────────────────────────

  /// Enqueue a command for sending.
  void send(String command) {
    if (bypassMode) {
      // ignore: avoid_print
      print('[BYPASS] $command');
      return;
    }
    _queue.add(command);
    if (!_processing) _processQueue();
  }

  /// Test connectivity: sends a handshake and waits for a UDP reply.
  /// Returns true if controller responds within [_testTimeout].
  Future<bool> testConnection() async {
    if (bypassMode) return true;
    RawDatagramSocket? sock;
    try {
      sock = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      sock.broadcastEnabled = false;

      final completer = Completer<bool>();
      Timer? timeout;

      // Set up listener (with error handler) BEFORE sending so async socket
      // errors are always captured and never become unhandled zone errors.
      sock.listen(
        (event) {
          if (event == RawSocketEvent.read) {
            final dg = sock?.receive();
            if (dg != null && dg.address.address == controllerIp) {
              if (!completer.isCompleted) completer.complete(true);
            }
          }
        },
        onError: (_) {
          if (!completer.isCompleted) completer.complete(false);
        },
        cancelOnError: true,
      );

      const cmd = '*#1PRGC30,0000';
      sock.send(cmd.codeUnits, InternetAddress(controllerIp), controllerPort);

      timeout = Timer(_testTimeout, () {
        if (!completer.isCompleted) completer.complete(false);
      });

      final result = await completer.future;
      timeout.cancel();
      return result;
    } catch (_) {
      return false;
    } finally {
      sock?.close();
    }
  }

  // ─── Private ───────────────────────────────────────────────────────────────

  Future<void> _processQueue() async {
    _processing = true;
    while (_queue.isNotEmpty) {
      final cmd = _queue.removeAt(0);
      await _sendNow(cmd);
      await Future.delayed(Duration(milliseconds: commandDelayMs));
    }
    _processing = false;
  }

  Future<void> _sendNow(String command) async {
    try {
      final sock = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      sock.send(command.codeUnits, InternetAddress(controllerIp), controllerPort);
      sock.close();
      // ignore: avoid_print
      print('[SENT] $command');
    } catch (e) {
      // ignore: avoid_print
      print('[UDP] send error: $e');
    }
  }

  void dispose() {
    _queue.clear();
    _processing = false;
  }
}
