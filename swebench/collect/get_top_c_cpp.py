import os
import json
import argparse
from ghapi.core import GhApi

# 设置 GitHub Token
gh_token = os.environ.get("GITHUB_TOKEN")
if not gh_token:
    msg = "Please set the GITHUB_TOKEN environment variable."
    raise ValueError(msg)
api = GhApi(token=gh_token)

def calculate_language_ratios(languages):
    """
    分别计算 C 和 C++ 代码在总代码中的占比

    Args:
        languages (dict): 包含仓库中每种语言的代码行数
    
    Returns:
        dict: 包含 C 和 C++ 的比例
    """
    total_lines = sum(languages.values())
    c_lines = languages.get('C', 0)
    cpp_lines = languages.get('C++', 0)
    
    c_ratio = c_lines / total_lines if total_lines > 0 else 0
    cpp_ratio = cpp_lines / total_lines if total_lines > 0 else 0
    
    return {
        "c_ratio": c_ratio,
        "cpp_ratio": cpp_ratio
    }

def fetch_all_pages(query, max_repos):
    """
    获取所有符合条件的项目（支持分页）

    Args:
        query (str): GitHub 搜索查询
        max_repos (int): 最大项目数量
    
    Returns:
        list: 所有符合条件的项目列表
    """
    repos = []
    page = 1
    per_page = 100  # GitHub API 每页最多返回 100 条结果
    while len(repos) < max_repos:
        print(f"Fetching page {page} for query: {query}")
        try:
            result = api.search.repos(q=query, sort="stars", order="desc", per_page=per_page, page=page, timeout=60)
            items = result["items"]
            if not items:  # 如果没有更多结果，退出循环
                break
            repos.extend(items)
            page += 1
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break
    return repos[:max_repos]  # 截取最多 max_repos 个项目

def get_github_projects_by_language(max_repos, output_file_c, output_file_cpp, min_rank, max_rank):
    """
    获取 GitHub 上排名靠前的 C 和 C++ 项目，并分别排名

    Args:
        max_repos (int): 最大项目数量
        output_file_c (str): C 项目的输出文件名
        output_file_cpp (str): C++ 项目的输出文件名
        min_rank (int): 最小排名（包含）
        max_rank (int): 最大排名（包含）
    """
    # 查询 C 和 C++ 项目
    query_c = "language:C"
    query_cpp = "language:C++"

    def fetch_and_filter_repos(query, language_key, ratio_threshold):
        """
        获取并筛选指定语言的项目

        Args:
            query (str): GitHub 搜索查询
            language_key (str): 语言键（'c_ratio' 或 'cpp_ratio'）
            ratio_threshold (float): 语言占比阈值
        
        Returns:
            list: 符合条件的项目列表
        """
        repos = fetch_all_pages(query, max_repos)  # 使用分页获取所有项目
        eligible_repos = []
        for repo in repos:
            # 获取仓库的语言分布
            languages = api.repos.list_languages(owner=repo['owner']['login'], repo=repo['name'])
            ratios = calculate_language_ratios(languages)
            
            # 筛选条件：语言占比大于阈值
            if ratios[language_key] >= ratio_threshold:
                eligible_repos.append(repo)
        
        # 按星标数重新排序
        eligible_repos.sort(key=lambda x: x["stargazers_count"], reverse=True)
        return eligible_repos

    # 获取 C 项目
    print("Fetching and filtering C projects...")
    eligible_c_repos = fetch_and_filter_repos(query_c, "c_ratio", 0.9)  
    print(f"Found {len(eligible_c_repos)} eligible C projects.")

    # 输出符合条件的项目
    with open(output_file_c, "w") as f_c:
        if len(eligible_c_repos) < min_rank:
            print(f"Not enough C projects to satisfy rank range ({min_rank}-{max_rank}). Found only {len(eligible_c_repos)} projects.")
        else:
            for rank, repo in enumerate(eligible_c_repos, start=1):
                if min_rank <= rank <= max_rank:
                    print(
                        json.dumps(
                            {
                                "rank": rank,
                                "name": repo["full_name"],
                                "url": repo["html_url"],
                                "stars": repo["stargazers_count"],
                                "forks": repo["forks_count"],
                                "c_ratio": calculate_language_ratios(api.repos.list_languages(owner=repo['owner']['login'], repo=repo['name']))["c_ratio"],
                            }
                        ),
                        file=f_c,
                        flush=True,
                    )

    # 获取 C++ 项目
    print("Fetching and filtering C++ projects...")
    eligible_cpp_repos = fetch_and_filter_repos(query_cpp, "cpp_ratio", 0.9)  # 
    print(f"Found {len(eligible_cpp_repos)} eligible C++ projects.")

    # 输出符合条件的项目
    with open(output_file_cpp, "w") as f_cpp:
        if len(eligible_cpp_repos) < min_rank:
            print(f"Not enough C++ projects to satisfy rank range ({min_rank}-{max_rank}). Found only {len(eligible_cpp_repos)} projects.")
        else:
            for rank, repo in enumerate(eligible_cpp_repos, start=1):
                if min_rank <= rank <= max_rank:
                    print(
                        json.dumps(
                            {
                                "rank": rank,
                                "name": repo["full_name"],
                                "url": repo["html_url"],
                                "stars": repo["stargazers_count"],
                                "forks": repo["forks_count"],
                                "cpp_ratio": calculate_language_ratios(api.repos.list_languages(owner=repo['owner']['login'], repo=repo['name']))["cpp_ratio"],
                            }
                        ),
                        file=f_cpp,
                        flush=True,
                    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-repos", help="Maximum number of repos to fetch", type=int, default=1000)
    parser.add_argument("--min-rank", help="Minimum rank (inclusive)", type=int, default=50)
    parser.add_argument("--max-rank", help="Maximum rank (inclusive)", type=int, default=100)
    args = parser.parse_args()

    output_file_c = "github_c_rankings.jsonl"
    output_file_cpp = "github_cpp_rankings.jsonl"

    get_github_projects_by_language(args.max_repos, output_file_c, output_file_cpp, args.min_rank, args.max_rank)