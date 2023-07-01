package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/cloudfoundry/noaa/consumer"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type (
	tokenRefresher struct {
		uaaURL       string
		refreshToken string
	}
	tokenResponse struct {
		AccessToken  string `json:"access_token"`
		RefreshToken string `json:"refresh_token"`
		TokenType    string `json:"token_type"`
	}
	infoResponse struct {
		UAAURL          string `json:"token_endpoint"`
		DopplerEndpoint string `json:"doppler_logging_endpoint"`
	}
)

func getConfiguration(cfhome string) (loggingURL, uaaURL, token string, err error) {
	var (
		homedir string
		f       *os.File
	)
	homedir, err = os.UserHomeDir()
	if err != nil {
		return
	}
	if strings.HasPrefix(cfhome, "~") {
		cfhome = strings.Replace(cfhome, "~", homedir, 1)
	}
	cfhome, err = filepath.Abs(cfhome)
	if err != nil {
		return
	}
	filename := filepath.Join(cfhome, ".cf", "config.json")
	f, err = os.Open(filename)
	if err != nil {
		return
	}
	defer f.Close()
	fmt.Fprintf(os.Stderr, "Found CF config in %s\n", filename)
	data := make(map[string]interface{})
	if err = json.NewDecoder(f).Decode(&data); err != nil {
		fmt.Fprintf(os.Stderr, "Error %v\n", err)
		return
	}
	if t, ok := data["RefreshToken"]; ok {
		token = t.(string)
	}
	if d, ok := data["DopplerEndPoint"]; ok {
		loggingURL = d.(string)
	}
	if u, ok := data["AuthorizationEndpoint"]; ok {
		uaaURL = u.(string)
	}
	if loggingURL == "" {
		err = fmt.Errorf("Logging URL is required")
	} else if uaaURL == "" {
		err = fmt.Errorf("UAA URL is required")
	} else if token == "" {
		err = fmt.Errorf("RefreshToken is required")
	}
	return
}

func newTokenRefresher(uaaURL, token string) (*tokenRefresher, error) {
	if token == "" {
		cfhome := os.Getenv("CF_HOME")
		homedir, err := os.UserHomeDir()
		if err != nil {
			return nil, err
		}
		if strings.HasPrefix(cfhome, "~") {
			cfhome = strings.Replace(cfhome, "~", homedir, 1)
		}
		cfhome, err = filepath.Abs(cfhome)
		if err != nil {
			return nil, err
		}
		filename := filepath.Join(cfhome, ".cf", "config.json")
		f, err := os.Open(filename)
		if err != nil {
			return nil, err
		}
		defer f.Close()
		fmt.Fprintf(os.Stderr, "Found CF config in %s\n", filename)
		data := make(map[string]interface{})
		if err := json.NewDecoder(f).Decode(&data); err != nil {
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error %v\n", err)
			}
			if t, ok := data["RefreshToken"]; ok {
				token = t.(string)
			}
		}
	}
	return &tokenRefresher{uaaURL, token}, nil
}

func (r *tokenRefresher) RefreshAuthToken() (string, error) {
	fmt.Fprintf(os.Stderr, "Refreshing auth token...\n")
	values := url.Values{
		"grant_type":    {"refresh_token"},
		"client_id":     {"cf"},
		"client_secret": {""},
		"refresh_token": {r.refreshToken},
	}
	res, err := http.PostForm(r.uaaURL+"/oauth/token", values)
	if err != nil {
		return "", err
	}
	token := &tokenResponse{}
	if err := json.NewDecoder(res.Body).Decode(token); err != nil {
		return "", err
	}
	res.Body.Close()
	return token.TokenType + " " + token.AccessToken, nil
}

func getInfo(apiURL string, info *infoResponse) error {
	fmt.Fprintf(os.Stderr, "Getting info...\n")
	res, err := http.Get(apiURL + "/v2/info")
	if err != nil {
		return err
	}
	if err := json.NewDecoder(res.Body).Decode(info); err != nil {
		return err
	}
	res.Body.Close()
	return nil
}

func main() {
	var (
		url       string
		token     string
		guid      string
		eventType string
		toJSON    bool
		interval  time.Duration
		stopafter time.Duration
		err       error
	)
	flag.StringVar(&url, "url", "", "CF API URL")
	flag.StringVar(&token, "token", "", "UAA token")
	flag.StringVar(&guid, "guid", "", "CF App GUID")
	flag.StringVar(&eventType, "eventtype", "", "Event Type")
	flag.BoolVar(&toJSON, "json", false, "Output as JSON")
	flag.DurationVar(&stopafter, "stopafter", 0, "Stop watching and exit after this interval")
	flag.DurationVar(&interval, "count", 0, "Log counts on this interval")
	flag.Parse()

	info := infoResponse{}
	if cfhome := os.Getenv("CF_HOME"); cfhome != "" {
		info.DopplerEndpoint, info.UAAURL, token, err = getConfiguration(cfhome)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error %v\n", err)
			return
		}
	} else {
		if err := getInfo(url, &info); err != nil {
			fmt.Fprintf(os.Stderr, "Error %v\n", err)
			return
		}
	}

	c := consumer.New(info.DopplerEndpoint, nil, nil)
	if tr, err := newTokenRefresher(info.UAAURL, token); err != nil {
		fmt.Fprintf(os.Stderr, "Error %v\n", err)
		return
	} else {
		c.RefreshTokenFrom(tr)
	}
	out, errs := c.Stream(guid, "")
	url = strings.Join([]string{info.DopplerEndpoint, "apps", guid, "stream"}, "/")
	fmt.Fprintf(os.Stderr, "Streaming logs for %v\n", url)
	var (
		stop   <-chan time.Time
		timer  *time.Timer
		counts map[string]int64
		msg    string
	)
	if stopafter > 0 {
		stop = time.After(stopafter)
	} else {
		stop = make(chan time.Time)
	}
	if interval > 0 {
		timer = time.NewTimer(interval)
	} else {
		timer = &time.Timer{C: make(chan time.Time)}
	}
loop:
	for {
		if counts == nil {
			counts = make(map[string]int64)
		}
		select {
		case e := <-errs:
			fmt.Fprintf(os.Stderr, "%v\n", e)
			break loop
		case <-timer.C:
			timer.Reset(interval)
			counts["timestamp"] = time.Now().UnixNano()
			if toJSON {
				if data, err := json.Marshal(counts); err != nil {
					fmt.Fprintf(os.Stderr, "Error %v\n", err)
				} else {
					fmt.Println(string(data))
				}
			} else {
				msg = ""
				for name, count := range counts {
					msg = fmt.Sprintf("%s %s:%v", msg, name, count)
				}
				fmt.Println(msg)
			}
			counts = nil
			continue loop
		case <-stop:
			break loop
		case ev := <-out:
			if interval > 0 {
				counts[ev.EventType.String()] += 1
				continue loop
			} else if eventType != "" && ev.EventType.String() != eventType {
				continue loop
			}
			if toJSON {
				if data, err := json.Marshal(ev); err != nil {
					fmt.Fprintf(os.Stderr, "Error %v\n", err)
				} else {
					fmt.Println(string(data))
				}
			} else {
				fmt.Println(ev)
			}
		}
	}
}
