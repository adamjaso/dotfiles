package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"math/big"
	"os"
	"path/filepath"
	"strings"
	"time"
)

var (
	CASerialNumber = big.NewInt(4096)
)

func readPEM(filename, blockType string) (*pem.Block, error) {
	data, err := ioutil.ReadFile(filename)
	if err != nil {
		return nil, err
	}
	block, _ := pem.Decode(data)
	if block == nil || block.Type != blockType {
		return nil, fmt.Errorf("key %q is %q not %q", filename, block.Type, blockType)
	}
	return block, nil
}

func writePEM(out io.Writer, data []byte, blockType string) error {
	return pem.Encode(out, &pem.Block{
		Type:  blockType,
		Bytes: data,
	})
}

func readPrivateKey(filename string) (*rsa.PrivateKey, error) {
	block, err := readPEM(filename, "RSA PRIVATE KEY")
	if err != nil {
		return nil, err
	}
	return x509.ParsePKCS1PrivateKey(block.Bytes)
}

func readCertificate(filename string) (*x509.Certificate, error) {
	block, err := readPEM(filename, "CERTIFICATE")
	if err != nil {
		return nil, err
	}
	return x509.ParseCertificate(block.Bytes)
}

func readCertificateRequest(filename string) (*x509.CertificateRequest, error) {
	block, err := readPEM(filename, "CERTIFICATE REQUEST")
	if err != nil {
		return nil, err
	}
	return x509.ParseCertificateRequest(block.Bytes)
}

func readPublicKey(filename string) (interface{}, error) {
	block, err := readPEM(filename, "PUBLIC KEY")
	if err != nil {
		return nil, err
	}
	return x509.ParsePKIXPublicKey(block.Bytes)
}

func randSerialNumber() *big.Int {
	serialNumber, err := rand.Int(rand.Reader, big.NewInt(1024*1024*1024*1024))
	if err != nil {
		panic(err)
	}
	return serialNumber
}

func createCert(cakeyfile, cacertfile, csrfile, pubkeyfile, commonName, usage string, validity time.Duration) {
	privkeyCA, err := readPrivateKey(cakeyfile)
	if err != nil {
		fmt.Println("readPrivateKey", err)
		return
	}
	var (
		parent       *x509.Certificate
		pubkeyToSign interface{}
	)
	if csrfile != "" {
		req, err := readCertificateRequest(csrfile)
		if err != nil {
			fmt.Println("readCertificateRequest", err)
			return
		} else if err := req.CheckSignature(); err != nil {
			fmt.Println("req.CheckSignature", err)
			return
		}
		commonName = req.Subject.CommonName
		pubkeyToSign = req.PublicKey
		fmt.Fprintf(os.Stderr, "signing     CSR\n", csrfile)
	} else if pubkeyfile != "" {
		pubkeyToSign, err = readPublicKey(pubkeyfile)
		if err != nil {
			fmt.Println("readPublicKey", err)
			return
		}
		fmt.Fprintf(os.Stderr, "signing     %s\n", pubkeyfile)
	} else {
		fmt.Fprintf(os.Stderr, "signing     CA\n")
		pubkeyToSign = privkeyCA.Public()
	}
	nb := time.Now()
	na := nb.Add(validity)
	template := &x509.Certificate{
		NotBefore:             nb,
		NotAfter:              na,
		BasicConstraintsValid: true,
		Subject: pkix.Name{
			CommonName: commonName,
		},
	}
	fmt.Fprintf(os.Stderr, "not_before  %s\n", nb.Format(time.RFC3339))
	fmt.Fprintf(os.Stderr, "not_after   %s\n", na.Format(time.RFC3339))
	fmt.Fprintf(os.Stderr, "common_name %s\n", commonName)
	if cacertfile != "" {
		parent, err = readCertificate(cacertfile)
		if err != nil {
			fmt.Println("readCertificate", err)
			return
		}
		fmt.Fprintf(os.Stderr, "parent      %s\n", cacertfile)
		fmt.Fprintf(os.Stderr, "self_signed false\n")
	} else {
		parent = template
		fmt.Fprintf(os.Stderr, "self_signed true\n")
	}
	switch usage {
	case "server":
		template.SerialNumber = randSerialNumber()
		template.ExtKeyUsage = []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}
	case "client":
		template.SerialNumber = randSerialNumber()
		template.ExtKeyUsage = []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth}
	case "ca":
		template.IsCA = true
		template.SerialNumber = CASerialNumber
	default:
		fmt.Println("unknown usage", usage)
		return
	}
	fmt.Fprintf(os.Stderr, "usage       %s\n", usage)
	fmt.Fprintf(os.Stderr, "serial_num  %s\n", template.SerialNumber)
	certbytes, err := x509.CreateCertificate(rand.Reader, template, parent, pubkeyToSign, privkeyCA)
	if err != nil {
		fmt.Println("x509.CreateCertificate", err)
		return
	}
	err = writePEM(os.Stdout, certbytes, "CERTIFICATE")
	if err != nil {
		fmt.Println("writePEM", err)
	}
}

func getCommonName(filename string) string {
	base := filepath.Base(filename)
	parts := strings.Split(base, ".")
	if len(parts) > 1 {
		return strings.Join(parts[:len(parts)-1], ".")
	}
	return base
}

func getFilenameWithExt(ext string) string {
	pat := "*." + ext
	if names, err := filepath.Glob(pat); err != nil {
		return ""
	} else if len(names) != 1 {
		return ""
	} else {
		return names[0]
	}
}

func main() {
	var (
		cakeyfile, cacertfile string
		pubkeyfile, csrfile   string
		commonName, usage     string
		validity              time.Duration
	)
	flag.StringVar(&cakeyfile, "cakey", "ca.key", "CA private key")
	flag.StringVar(&cacertfile, "ca", "", `CA certificate file (default "ca.crt")`)
	flag.StringVar(&csrfile, "csr", "", `CSR file (default "*.csr")`)
	flag.StringVar(&pubkeyfile, "pubkey", "", `Public key to sign file (default "*.pub")`)
	flag.StringVar(&commonName, "commonname", "", `Certificate Subject Common Name (default pubkey or csrfile name without extension)`)
	flag.StringVar(&usage, "usage", "", "Certificate usage. Choices: ca|server|client")
	flag.DurationVar(&validity, "validity", 24*365*time.Hour, "Certificate validity interval")
	flag.Parse()

	if usage == "" {
		fmt.Println("-usage is required")
		return
	} else if usage == "ca" {
		if commonName == "" {
			commonName = "default-ca"
		}
		if csrfile != "" || pubkeyfile != "" {
			fmt.Println("-csrfile and -pubkeyfile are not allowed with -usage ca")
			return
		}
	} else {
		if cacertfile == "-" {
			cacertfile = ""
		} else if cacertfile == "" {
			cacertfile = "ca.crt" // default to ca.crt
		}
		if csrfile == "" && pubkeyfile == "" {
			csrfile = getFilenameWithExt("csr")    // try *.csr
			pubkeyfile = getFilenameWithExt("pub") // try *.pub
		}
		if csrfile != "" {
			if commonName == "" {
				commonName = getCommonName(csrfile) // use csr filename without ext
			}
		} else if pubkeyfile != "" {
			if commonName == "" {
				commonName = getCommonName(pubkeyfile) // use pubkey filename without ext
			}
		}
		if csrfile == "" && pubkeyfile == "" {
			fmt.Printf("-csrfile or -pubkeyfile is required for -usage %s\n", usage)
			return
		}
	}
	if csrfile == "" && commonName == "" {
		fmt.Println("-csrfile or -commonname is required")
		return
	}
	createCert(cakeyfile, cacertfile, csrfile, pubkeyfile, commonName, usage, validity)
}
