FROM golang:1.21 AS build
WORKDIR /app
COPY . .
RUN go build -o server .
FROM gcr.io/distroless/base
COPY --from=build /app/server /server
ENTRYPOINT ["/server"]
