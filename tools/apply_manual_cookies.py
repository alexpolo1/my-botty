def main():
    # Netscape format: domain \t TRUE/FALSE \t path \t TRUE/FALSE \t expiry \t name \t value
    # Expiry 2000000000 is roughly the year 2033.
    cookies = [
        (".d2jsp.org\tTRUE\t/\tFALSE\t2000000000\tmember_id\t1257929"),
        (".d2jsp.org\tTRUE\t/\tFALSE\t2000000000\tmsec\tad20300cfcab43babd82d0a5cc3c9515"),
    ]
    
    with open("cookies.txt", "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("\n".join(cookies) + "\n")
    print("Successfully created cookies.txt with manual session data.")

if __name__ == "__main__":
    main()
