from database_tests.helper import *
from gdb_clients import *
from configs.conf import new_logger, config
import csv
from mutator.redis.query_transformer import QueryTransformer

def compare(list1, list2):
    if len(list1) != len(list2):
        return False
    if len(list1) >= 9000:
        return True
    lst1 = [i.__str__() for i in list1]
    lst2 = [i.__str__() for i in list2]
    lst1.sort()
    lst2.sort()
    return lst1 == lst2

def oracle(conf: TestConfig, result1, result2):
    if not compare(result1[0], result2[0]):
        if conf.mode == 'live':
            conf.report(conf.report_token,f"[{conf.database_name}][{conf.source_file}]Logic inconsistency",
                        f"{conf.q1}\n{conf.q2}")
            conf.num_bug_triggering += 1
        conf.logger.warning({
            "database_name": conf.database_name,
            "source_file": conf.source_file,
            "tag": "logic_inconsistency",
            "query1": conf.q1,
            "query2": conf.q2,
            "query_res1": result1[0].__str__(),
            "query_res2": result2[0].__str__(),
            "query_time1": result1[1],
            "query_time2": result2[1],
            })
        with open(conf.logic_inconsistency_trace_file, mode='a', newline='') as file:
            writer = csv.writer(file, delimiter='\t')
            writer.writerow([conf.database_name, conf.source_file, conf.q1, conf.q2])

    big = max(result1[1], result2[1])
    small = min(result1[1], result2[1])
    heap = MaxHeap("logs/redis_performance.json",10)
    metric = big/(small+100)
    if metric > 1:
        heap.insert(metric)
    threshold = heap.get_heap()
    if metric in threshold:
        if conf.mode == 'live':
            conf.report(conf.report_token,f"[{conf.database_name}][{conf.source_file}][{big}ms,{small}ms]Performance inconsistency",
                        conf.q1 + "\n" + conf.q2)
            conf.num_bug_triggering += 1
        conf.logger.warning({
            "database_name": conf.database_name,
            "source_file": conf.source_file,
            "tag": "performance_inconsistency",
            "query1": conf.q1,
            "query2": conf.q2,
            "query_res1": result1[0].__str__(),
            "query_res2": result2[0].__str__(),
            "query_time1": result1[1],
            "query_time2": result2[1],
            })


class RedisTester(TesterAbs):
    def __init__(self, database):
        self.database = database

    def single_file_testing(self, logfile):
        def query_producer():
            with open(logfile, 'r') as f:
                content = f.read()
            contents = content.strip().split('\n')
            query_statements = contents[-5000:]
            create_statements = contents[4:-5000]
            return create_statements, query_statements

        logger = new_logger("logs/redis.log", True)
        qt = QueryTransformer()
        conf = TestConfig(
            client=Redis("10.20.10.27", self.database),
            logger=logger,
            source_file=logfile,
            logic_inconsistency_trace_file='logs/redis_logic_error.tsv',
            database_name='redis',
            query_producer_func=query_producer,
            oracle_func=oracle,
            report_token=config.get('lark', 'redis'),
            mutator_func=qt.mutant_query_generator
        )
        general_testing_procedure(conf)
        return True

    def single_file_testing_alt(self, logfile, create_statements, query_statements):
        def query_producer():
            return create_statements, query_statements

        logger = new_logger("logs/redis.log", True)
        qt = QueryTransformer()
        conf = TestConfig(
            client=Redis("10.20.10.27", self.database),
            logger=logger,
            source_file=logfile,
            logic_inconsistency_trace_file='logs/redis_logic_error.tsv',
            database_name='redis',
            query_producer_func=query_producer,
            oracle_func=oracle,
            report_token=config.get('lark', 'redis'),
            mutator_func=qt.mutant_query_generator
        )
        general_testing_procedure(conf)
        return conf.num_bug_triggering


def schedule():
    scheduler(config.get('redis', 'input_path'), RedisTester(f"redis_misc"), "redis")


if __name__ == "__main__":
    if config.get('GLOBAL', 'env') == "debug":
        Tester = RedisTester('dev_graph')
        Tester.single_file_testing("./query_producer/logs/composite/database263-cur.log")
    else:
        schedule()
