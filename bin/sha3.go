package main

import (
	"encoding/hex"
	"flag"
	"fmt"
	"golang.org/x/crypto/sha3"
	"hash"
	"io"
	"os"
)

func GetAlgorithmHash(id int) hash.Hash {
	switch id {
	case 224:
		return sha3.New224()
	case 256:
		return sha3.New256()
	case 384:
		return sha3.New384()
	case 512:
		return sha3.New512()
	default:
		return nil
	}
}

func main() {
	var (
		alg int
	)
	flag.IntVar(&alg, "a", 256, "SHA algorithm (choose from: 224, 256, 384, 512; default is 256)")
	flag.Parse()
	algHash := GetAlgorithmHash(alg)
	if _, err := io.Copy(algHash, os.Stdin); err != nil {
		fmt.Println(err)
	} else {
		hashBytes := algHash.Sum(nil)
		fmt.Println(hex.EncodeToString(hashBytes[:]))
	}
}
