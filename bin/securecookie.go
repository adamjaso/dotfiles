package main

/*
Encodes and decodes gorilla/securecookie encrypted cookies.

Build instructions:

 GO111MODULE=off go get -v github.com/gorilla/securecookie
 GO111MODULE=off go build ~/bin/securecookie.go

Working example:

 export COOKIE_HASH_KEY=abcdefghijklmnopqrstuvwxyz012345 COOKIE_BLOCK_KEY=abcdefghijklmnopqrstuvwxyz012345

 # encrypt

 $ echo '{"key":"value"}' | ./securecookie -encode -name cookie-name
 MTY0MDIwMjExNXxoSmRXdHlRbTFMOGtQZk1RNkV0ZFRBN2c1aEhEeS0yN0FtZFROOVJmNGk0PXy8kXjlgqp5OSX_IFkDNwp3i4hjOvj8HonvBqjZ-ljREw==

 # decrypt

 $ echo MTY0MDIwMjExNXxoSmRXdHlRbTFMOGtQZk1RNkV0ZFRBN2c1aEhEeS0yN0FtZFROOVJmNGk0PXy8kXjlgqp5OSX_IFkDNwp3i4hjOvj8HonvBqjZ-ljREw== | \
   ./securecookie -decode -name cookie-name
 {"key":"value"}

*/

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/gorilla/securecookie"
	"io/ioutil"
	"os"
)

func usage() {
	fmt.Fprintf(os.Stderr, `Usage: %s 

Encodes and decodes gorilla/securecookie encrypted cookies.

Environment variables COOKIE_HASH_KEY and COOKIE_BLOCK_KEY are required.
If -decode, then stdin should be ciphertext, else if -decode, then stdin should be JSON.

Arguments:
`, os.Args[0])
	flag.PrintDefaults()
}

func main() {
	flag.Usage = usage
	var (
		cookie                  *securecookie.SecureCookie
		hashKey, blockKey, name string
		decode, encode          bool
	)
	flag.StringVar(&name, "name", "", "cookie name")
	flag.BoolVar(&decode, "decode", false, "decode a cookie value")
	flag.BoolVar(&encode, "encode", false, "encode a cookie value")
	flag.Parse()

	hashKey = os.Getenv("COOKIE_HASH_KEY")
	blockKey = os.Getenv("COOKIE_BLOCK_KEY")
	if hashKey == "" || blockKey == "" {
		flag.Usage()
		return
	}
	data := make(map[string]interface{})
	cookie = securecookie.New([]byte(hashKey), []byte(blockKey))
	cookie.SetSerializer(securecookie.JSONEncoder{})
	if decode {
		if valueBytes, err := ioutil.ReadAll(os.Stdin); err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
		} else if err := cookie.Decode(name, string(valueBytes), &data); err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
		} else if err := json.NewEncoder(os.Stdout).Encode(data); err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
		}
	} else if encode {
		if err := json.NewDecoder(os.Stdin).Decode(&data); err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
		} else if encoded, err := cookie.Encode(name, &data); err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
		} else {
			fmt.Println(encoded)
		}
	} else {
		flag.Usage()
	}
}
