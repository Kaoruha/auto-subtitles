import os
import tempfile
import subprocess
import shutil
import hashlib
import json

root_dir = "/home/kaoru/smbshare/Course/WarriorProTrading2021"


def generage_file_hash(file_path, block_size=65536):
    print(f"计算Hash: {file_path}")
    file_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        fb = f.read(block_size)
        while len(fb) > 0:
            file_hash.update(fb)
            fb = f.read(block_size)
    return file_hash.hexdigest()


def load_processed_videos(file="./processed_videos.json"):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}


def add_processed_videos(video_path, record_file="./processed_videos.json"):
    print(f"添加 {video_path} 至已处理")
    key = "processed_videos"
    raw = load_processed_videos(record_file)
    if key in raw.keys():
        raw[key].append(generage_file_hash(video_path))
        data = raw
    else:
        data = {"processed_videos": [generage_file_hash(video_path)]}
    with open(record_file, "w") as f:
        json.dump(data, f)


# 检查视频是否已处理过
def is_video_processed(video_path):
    key = "processed_videos"
    hash = generage_file_hash(video_path)
    raw = load_processed_videos()
    if key not in raw.keys():
        return False
    if hash in raw[key]:
        return True
    return False


def find_videos(directory, extensions=(".mp4", ".mkv")):
    video_files = []
    # 使用 os.walk 遍历所有子目录和文件
    for root, dirs, files in os.walk(directory):
        for file in files:
            # 检查文件扩展名是否符合要求
            if file.lower().endswith(extensions):
                video_files.append(os.path.join(root, file))
    return video_files


def extract_audio_with_ffmpeg(video_file, output_wav):
    # 使用 ffmpeg 提取音频为 wav 格式
    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_file,  # 输入视频文件
        "-q:a",
        "0",  # 不需要视频部分
        "-map",
        "0:a:0?",
        "-c:a",
        "pcm_s16le",
        output_wav,  # 输出临时 wav 文件
    ]
    subprocess.run(command, check=True)


def transcribe_audio_with_whisper(wav_file):
    # 使用 whisper 将音频转换为 srt 字幕
    command = [
        "whisper",
        wav_file,
        "--model",
        "medium",
        "--task",
        "translate",
        "--language",
        "zh",
        "-o",
        "/tmp",
        "--output_format",
        "srt",
    ]
    subprocess.run(command, check=True)


def process_videos(video_files):
    failed_list = []
    done_count = 0
    pass_count = 0
    for video_file_path in video_files:
        # Check
        # 获取视频的基本文件名（不带扩展名）
        if is_video_processed(video_file_path):
            print(f"{video_file_path} already processed.")
            pass_count += 1
            continue
        base_name = os.path.splitext(os.path.basename(video_file_path))[0]
        video_dir = os.path.dirname(video_file_path)

        # 生成临时的 wav 文件
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                temp_wav_file = tmp_wav.name
                print(f"提取音频: {video_file_path}")
                # 调用 ffmpeg 提取音频
                extract_audio_with_ffmpeg(video_file_path, temp_wav_file)
                # 调用 whisper 将 wav 文件转换为 srt 字幕
                temp_srt_file = os.path.splitext(temp_wav_file)[0] + ".srt"
                print(f"转录音频到字幕: {temp_srt_file}")
                transcribe_audio_with_whisper(temp_wav_file)
                print(f"移出音频: {temp_wav_file}")
                os.remove(temp_wav_file)
                # # 定义 srt 文件的最终输出路径
                srt_file_path = os.path.join(video_dir, base_name + ".srt")
                # # 将临时 srt 文件拷贝到视频所在目录
                print(f"将字幕文件拷贝到: {srt_file_path}")
                shutil.copy(temp_srt_file, srt_file_path)
                add_processed_videos(video_file_path)
                done_count += 1
        except Exception as e:
            print(e)
            failed_list.append(video_file_path)
        finally:
            print(f"成功生成{done_count}个字幕.")
            print(f"以下 {len(failed_list)}个文件生成失败,请手动检查:")
            for i in failed_list:
                print(i)


if __name__ == "__main__":
    video_files = find_videos(root_dir)
    process_videos(video_files)
