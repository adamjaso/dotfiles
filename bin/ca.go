package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/pem"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"math/big"
	"net"
	"net/url"
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

func createCert(cakeyfile, cacertfile, csrfile, pubkeyfile, commonName, usage, san string, validity time.Duration) {
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
	if err := setSAN(template, san); err != nil {
		fmt.Printf("invalid SAN %v\n", err)
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

func setSAN(cert *x509.Certificate, san string) error {
	for _, pair := range strings.Split(san, "/") {
		parts := strings.SplitN(pair, ":", 2)
		if len(parts) <= 1 {
			continue
		}
		santype := parts[0]
		values := strings.Split(parts[1], ",")
		switch santype {
		case "dns":
			cert.DNSNames = values
			for _, v := range values {
				fmt.Fprintf(os.Stderr, "dns         %s\n", v)
			}
		case "email":
			cert.EmailAddresses = values
			for _, v := range values {
				fmt.Fprintf(os.Stderr, "email       %s\n", v)
			}
		case "ip":
			cert.IPAddresses = make([]net.IP, len(values))
			for i, v := range values {
				ip := net.ParseIP(v)
				if ip == nil {
					return fmt.Errorf("invalid IP %s", v)
				}
				cert.IPAddresses[i] = ip
				fmt.Fprintf(os.Stderr, "ip          %s\n", v)
			}
		case "uri":
			cert.URIs = make([]*url.URL, len(values))
			for i, v := range values {
				uval, e := base64.StdEncoding.DecodeString(v)
				if e != nil {
					return fmt.Errorf("invalid URI %s must be base64 encoded %v", v, e)
				}
				u, e := url.Parse(strings.TrimSpace(string(uval)))
				if e != nil {
					return fmt.Errorf("invalid URI %s %v", v, e)
				}
				cert.URIs[i] = u
				fmt.Fprintf(os.Stderr, "uri         %s\n", u.String())
			}
		}
	}
	return nil
}

func getCommonName(filename string) string {
	base := filepath.Base(filename)
	parts := strings.Split(base, ".")
	if len(parts) > 1 {
		return strings.Join(parts[:len(parts)-1], ".")
	}
	return base
}

func getFilenameWithExt(exts ...string) string {
	for _, ext := range exts {
		pat := "*." + ext
		if names, err := filepath.Glob(pat); err != nil {
			return ""
		} else if len(names) != 1 {
			return ""
		} else {
			return names[0]
		}
	}
	return ""
}

func main() {
	var (
		cakeyfile, cacertfile string
		pubkeyfile, csrfile   string
		commonName, usage     string
		san                   string
		validity              time.Duration
	)
	flag.StringVar(&cakeyfile, "cakey", "ca.key", "CA private key")
	flag.StringVar(&cacertfile, "ca", "", `CA certificate file (default "ca.crt")`)
	flag.StringVar(&csrfile, "csr", "", `CSR file (default "*.csr" or "*.req")`)
	flag.StringVar(&pubkeyfile, "pubkey", "", `Public key to sign file (default "*.pub")`)
	flag.StringVar(&commonName, "commonname", "", `Certificate Subject Common Name (default: -usage ca => default-ca, -usage client|server => from -csr or -pubkey)`)
	flag.StringVar(&usage, "usage", "", "Certificate usage. Choices: ca|server|client")
	flag.StringVar(&san, "subjectalternatenames", "", "Subject Alternate Names, slash separated groups formatted as type:value1,value2, i.e. ip:x,y/uri:x,y/email:x,y/dns:x,y")
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
			fmt.Println("-csr and -pubkey are not allowed with -usage ca")
			return
		}
	} else {
		if cacertfile == "-" {
			cacertfile = ""
		} else if cacertfile == "" {
			cacertfile = "ca.crt" // default to ca.crt
		}
		if csrfile == "" && pubkeyfile == "" {
			csrfile = getFilenameWithExt("csr", "req") // try *.csr
			pubkeyfile = getFilenameWithExt("pub")     // try *.pub
		}
		if csrfile != "" {
			if commonName != "" {
				fmt.Println("-csr overrides -commonname")
				return
			}
		} else if pubkeyfile != "" {
			if commonName == "" {
				commonName = getCommonName(pubkeyfile) // use pubkey filename without ext
			}
		}
		if csrfile == "" {
			if pubkeyfile == "" {
				fmt.Printf("-csr or -pubkey is required for -usage %s\n", usage)
				return
			}
			if commonName == "" {
				fmt.Println("-csr or -commonname and -pubkey is required")
				return
			}
		}
	}
	createCert(cakeyfile, cacertfile, csrfile, pubkeyfile, commonName, usage, san, validity)
}
