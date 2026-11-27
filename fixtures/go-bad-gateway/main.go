package main

import (
	"context"
	"net/http"
	"os"

	openai "github.com/sashabaranov/go-openai"
)

var client = openai.NewClient(os.Getenv("OPENAI_API_KEY"))
var sessions = make(map[string][]string)

func ask(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query().Get("q")
	sessions["default"] = append(sessions["default"], q)
	resp, err := client.CreateChatCompletion(context.Background(), openai.ChatCompletionRequest{
		Messages: []openai.ChatCompletionMessage{{Role: "user", Content: q}},
	})
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	w.Write([]byte(resp.Choices[0].Message.Content))
}

func main() {
	http.HandleFunc("/ask", ask)
	http.ListenAndServe(":8080", nil)
}
