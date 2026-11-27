package com.example;

import com.openai.client.OpenAIClient;
import java.util.HashMap;
import java.util.Map;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class AiController {
    private static Map<String, String> sessions = new HashMap<>();

    @PostMapping("/ask")
    public String ask(String q) {
        sessions.put("default", q);
        return openai.chat(q);
    }

    public String run(String generatedCode) throws Exception {
        ProcessBuilder pb = new ProcessBuilder("sh", "-c", generatedCode);
        return new String(pb.start().getInputStream().readAllBytes());
    }
}
