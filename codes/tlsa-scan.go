package main

import (
	"os"
	"strconv"
	"log"
	"sync"
	"bufio"
	"encoding/base64"

	"github.com/miekg/dns"
	"github.com/miekg/unbound"
)

func main() {
	args := os.Args[1:]
	city := args[0] // location of the scanning server, ex) virginia
	numThreads, _ := strconv.Atoi(args[1]) // the number of threads
	inputFile := args[2] // seed file
	outputPath := args[3] // path of the output file

	u := unbound.New()
	defer u.Destroy()

	slabs := "256"
	
	if err := u.Hosts("/etc/hosts"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}

	if err := u.AddTaFile("/home/ubuntu/dane/keys/keys"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}

	if err := u.SetOption("qname-minimisation", "no"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("msg-cache-slabs", slabs); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("rrset-cache-slabs", slabs); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("infra-cache-slabs", slabs); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("key-cache-slabs", slabs); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("rrset-cache-size", "50m"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("msg-cache-size", "25m"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("outgoing-range", "1024"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("num-queries-per-thread", "512"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("so-sndbuf", "4m"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("so-rcvbuf", "4m"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	if err := u.SetOption("do-ip6", "no"); err != nil {
		log.Fatalf("error %s\n", err.Error())
	}
	

	jobs := make(chan string)
	var wg sync.WaitGroup

	for w := 0; w < numThreads; w++ {
		wg.Add(1)
		go run(jobs, city, u, strconv.Itoa(w), outputPath, &wg)
	}

	inputf, err := os.Open(inputFile)
	if err != nil {
		println(err.Error())
	}
	scanner := bufio.NewScanner(inputf)

	for scanner.Scan() {
		jobs <- scanner.Text()
	}
	close(jobs)
	wg.Wait()

}

func run(jobs <- chan string, city string, u *unbound.Unbound, idx string, outputPath string, wg *sync.WaitGroup){
	defer wg.Done()
	
	output := outputPath + "tlsa_" + idx + ".txt"
	f, err:= os.Create(output)
	if err != nil {
		println("Cannot write output -", outputPath)
	}

	for dn := range jobs {
		r, err := u.Resolve(dn, dns.TypeTLSA, dns.ClassINET)
		if err != nil {
			println("resolve error: ", err.Error())
			_, _ = f.WriteString(dn + " " + err.Error())
		}

		var result string
		if r.HaveData {
			if r.Secure {
				result = "Secure"
			} else if r.Bogus {
				result = "Bogus, " + r.WhyBogus
			} else {
				result = "Insecure"
			}

			answer, _ := r.AnswerPacket.Pack()
			enc := base64.StdEncoding.EncodeToString(answer)

			result = dn + ", " + city + ", " + result + ", " + enc
		} else {
			result = dn + ", " + city + ", NoData"
		}

		_, err = f.WriteString(result + "\n")
		if err != nil {
			println("Cannot write output -", outputPath)
		}
		f.Sync()
	}
}
