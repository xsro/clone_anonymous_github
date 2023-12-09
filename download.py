import argparse
import requests
from pathlib import Path
from time import sleep
import concurrent.futures

description="""Clone files from https://anonymous.4open.science
run 'pip3 install requests' to install dependencies
run 'python3 download.py --help' to show more options
examples: 
    python3 download.py --name 840c8c57-3c32-451e-bf12-0e20be300389
    python3 download.py --url https://anonymous.4open.science/r/840c8c57-3c32-451e-bf12-0e20be300389/
"""

def parse_args():
    parser = argparse.ArgumentParser(description='Clone from the https://anonymous.4open.science')
    parser.add_argument('--dir', type=str, 
                        help='save dir')
    parser.add_argument('--url', type=str,
                        help='target anonymous github link eg., https://anonymous.4open.science/r/840c8c57-3c32-451e-bf12-0e20be300389/')
    parser.add_argument('--name', type=str,
                        help='target anonymous github link id eg., 840c8c57-3c32-451e-bf12-0e20be300389, if specified this url will be ignored')
    parser.add_argument('--max-conns', type=int, default=2,
                        help='max connections number')
    parser.add_argument("--proxy",type=str,help="proxy server")
    parser.add_argument("--skip",type=list,default=["pyc"],help="file suffix to skip download default is pyc")
    return parser.parse_args()

def dict_parse(dic, pre=None):
    pre = pre[:] if pre else []
    if isinstance(dic, dict):
        for key, value in dic.items():
            if isinstance(value, dict):
                for d in dict_parse(value, pre + [key]):
                    yield d
            else:
                yield pre + [key, value]
    else:
        yield pre + [dic]

proxies=None
def req_url(dl_file, max_retry=5):
    url = dl_file[0]
    save_path = Path(dl_file[1])
    save_dir = save_path.parent
    save_dir.mkdir(exist_ok=True,parents=True)
    if save_path.exists():
        with open(save_path,"r") as f:
            line=f.readline()
            if "Please try again later." in line:
                pass
            else:
                return
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15"
    }
    for i in range(max_retry):
        try:
            r = requests.get(url, headers=headers,proxies=proxies)
            if "Please try again later." in r.text:
                print(r.text)
                print("please rerun this after some time")
                return False
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
        except Exception as e:
            print('file request exception (retry {}): {} - {}'.format(i, e, save_path))
            sleep(0.4)


if __name__ == '__main__':
    args = parse_args()

    url = args.url
    name = args.name
    if name is None:
        segs=url.split('/')
        for i,s in enumerate(segs):
            if s=="r":
                name=segs[i+1]
    max_conns = args.max_conns
    if args.dir is None:
        output_dir=Path(name)
    else:
        output_dir=Path(args.dir)
    output_dir.mkdir(exist_ok=True,parents=True)
    skips=args.skip
    if args.proxy:
        if args.proxy.startswith("http"):
            proxies={"https":"http://"+args.proxy}
        else:
            proxies={"https":args.proxy}
    print(f"[*] cloning project:{name}")
    print(f"\tproxy",proxies)
    print(f"\toutput to dir",output_dir)
    print(f"\tmax connections",max_conns)
    
    list_url = "https://anonymous.4open.science/api/repo/"+ name +"/files/"
    headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15"
    }
    resp = requests.get(url=list_url, headers=headers,proxies=proxies)
    if "Please try again later." in resp.text:
        print(resp.text)
        exit(1)
    file_list = resp.json()
    file_list=dict_parse(file_list)


    print("[*] downloading files:")
    
    dl_url = "https://anonymous.4open.science/api/repo/"+ name +"/file/"
    files = []
    out = []
    for file in file_list:
        file_path = "/".join(file[-len(file):-2]) # * operator to unpack the arguments out of a list
        save_path = output_dir.joinpath(file_path)
        file_url = f"https://anonymous.4open.science/api/repo/{name}/file/{file_path}"
        if any([file_url.endswith(s) for s in skips]):
            continue
        files.append((file_url, str(save_path)))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_conns) as executor:
        future_to_url = (executor.submit(req_url, dl_file) for dl_file in files)
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data==False:
                    executor.shutdown()
            except Exception as exc:
                data = str(type(exc))
            finally:
                out.append(data)

                print(f"{len(out)}/{len(files)}",end="\r")
    
    print("[*] files saved to:" + output_dir)